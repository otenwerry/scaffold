import math
import torch
import sys
from transformers import GPT2LMHeadModel, GPT2TokenizerFast, pipeline
from transformers import T5ForConditionalGeneration, T5Tokenizer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
import numpy as np

tokenizer = GPT2TokenizerFast.from_pretrained('gpt2')
model = GPT2LMHeadModel.from_pretrained('gpt2')
model.eval()

#summarizer = pipeline("summarization", model="facebook/bart-large-cnn")
summarizer = T5ForConditionalGeneration.from_pretrained("t5-base")
summary_tokenizer = T5Tokenizer.from_pretrained("t5-base")
embedder = SentenceTransformer("all-MiniLM-L6-v2")

#beginning of sentence token id
bos_id = tokenizer.bos_token_id 

@torch.no_grad() #decorator to disable gradient computation to optimize performance
#computesthe probabilities of the next token given the history
def q_prob(token_id: int, history_ids: torch.Tensor) -> float:
    #feeds the history to gpt2 model to get logits
    outputs = model(history_ids)
    logits = outputs.logits #shape (1, T, V)
    #gets the logits for the last token in the sequence
    last_logits = logits[0, -1, :] #shape (V,)
    #softmax(logits) = probabilities. we do log probabilities for numerical reasons.
    log_probs = torch.log_softmax(last_logits, dim=-1)
    #returns the probabilities of the next token,
    #doing exp to cancel the log
    return float(torch.exp(log_probs[token_id]))


#computes the bits of information content in a string of english text
def info_content(text: str):
    #tokenizes text string into token ids
    enc = tokenizer(text, return_tensors='pt')
    ids = enc.input_ids[0] #Shape (N,)
    #iterate through the tokens and add the entropy of each,
    #starting at 1 because the first token has no history
    total_bits = 0.0
    for i in range(1,len(ids)):
        #takes the first i tokens and adds a dimension
        history_ids = ids[:i].unsqueeze(0) #Shape (1,i)
        #gets the probability of the next token
        p_next = q_prob(int(ids[i]), history_ids)
        #if probability is 0, the log is -inf, which is bad; and probabilities can't be < 0.
        #softmax returns nonzero probabilities anyway.
        if p_next <= 0:
            raise ValueError(f"Invalid probability: {tokenizer.decode(ids[i])}")
        #add bits of this next token: I(x) = -log_2(p(x))
        total_bits += -math.log2(p_next)
        avg_bits = total_bits/(len(ids) - 1)
    #returns total bits and bits per token
    #we subtract 1 for the average because we didn't compute bits of first token
    return total_bits, avg_bits


'''#natural language compression
#we use bart because it's fine tuned for summarization/denoising
def compress(text: str, max_length_ratio: float):
    max_length = int(len(text.split()) * max_length_ratio)
    summary = summarizer(text, max_length=max_length, min_length=10)[0]['summary_text']
    return summary
'''

def compress(text: str, ratio: float):
    results = []
    current_text = text
    target_length = int(len(text.split()) * ratio)
    prompt = f"summarize in {target_length} words: {text}"
    inputs = summary_tokenizer(prompt, return_tensors="pt")
    outputs = summarizer.generate(inputs.input_ids, max_length=target_length + 10, min_length=10)
    compressed = summary_tokenizer.decode(outputs[0], skip_special_tokens=True)
    return compressed





#lookup table for background probabilities of each token
bos_id = tokenizer.bos_token_id #beginning of sentence token id
with torch.no_grad():
    #get the logits for the first token after the beginning of sentence token,
    #i.e. the first token in the sentence, and softmax to get probabilities
    out = model(torch.tensor([[bos_id]]))
    logits = out.logits[0, -1, :]
    p_bg_dist = torch.softmax(logits, dim=-1)

#computes the bits of information content in a string of english text,
#corrected for the background probability of each token
#(aka negative PMI?)
def info_content_background_corrected(text: str):
    enc = tokenizer(text, return_tensors='pt')
    ids = enc.input_ids[0]
    total_bits = 0.0

    #compute bits of information content like before, 
    #but subtract the background probability
    for i in range(1,len(ids)):
        history_ids = ids[:i].unsqueeze(0)
        p_next = q_prob(int(ids[i]), history_ids)
        if p_next <= 0:
            raise ValueError(f"Invalid probability: {tokenizer.decode(ids[i])}")
        p_bg = p_bg_dist[int(ids[i])]
        total_bits += -math.log2(p_next) + math.log2(p_bg)
        avg_bits = total_bits/(len(ids) - 1)
    return total_bits, avg_bits




if __name__ == "__main__":
    #if you want line breaks, you need to format it this way 
    # rather than with triple quotes, for token reasons
    
    sample = ( 
        "There is currently a lively, ongoing controversy among many sociologists and other professionals who study human nature : theories are being spun and arguments are being conducted among them about what it means that so many young people—and older people, for that matter—who live in our society today are so very interested in stories about zombies.?"
    )
    total_bits, per_token_bits = info_content(sample)
    print(sample)
    print(f"Character count: {len(sample)}")
    print(f"Total tokens: {total_bits / per_token_bits}")
    print(f"Total bits: {total_bits:.2f}")
    print(f"Bits per token: {per_token_bits:.2f}")
    for ratio in [0.8, 0.6, 0.4, 0.2]:
        compression = compress(sample, ratio)
        original_embedding = embedder.encode(sample)
        compressed_embedding = embedder.encode(compression)
        print(f"Compressed with T5: {compression}")
        print(f"Cosine similarity: {cosine_similarity([original_embedding], [compressed_embedding])[0][0]}")