import math
import torch
import sys
import os
from transformers import GPT2LMHeadModel, GPT2TokenizerFast, pipeline
from transformers import T5ForConditionalGeneration, T5Tokenizer
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
import numpy as np
#from allennlp.predictors.predictor import Predictor
#import allennlp_models.tagging
import glob
import nltk
import re

#initialize models
tokenizer = GPT2TokenizerFast.from_pretrained('gpt2')
model = GPT2LMHeadModel.from_pretrained('gpt2')
model.eval()
summarizer = T5ForConditionalGeneration.from_pretrained("t5-base")
summary_tokenizer = T5Tokenizer.from_pretrained("t5-base", legacy=True)
embedder = SentenceTransformer("all-mpnet-base-v2", device="cpu")
#openie = StanfordOpenIE()
#srl = semantic role labeling
#srl_predictor = Predictor.from_path("https://storage.googleapis.com/allennlp-public-models/structured-prediction-srl-bert.2020.12.15.tar.gz")

#turn off a flag to avoid tokenizer warnings
os.environ["TOKENIZERS_PARALLELISM"] = "false"

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

#natural language compression, using t5
def compress(text: str, ratio: float):
    target_length = int(len(text.split()) * ratio)
    prompt = f"summarize in {target_length} words: {text}"
    inputs = summary_tokenizer(prompt, return_tensors="pt")
    outputs = summarizer.generate(inputs.input_ids, max_length=target_length + 10, min_length=10)
    compressed = summary_tokenizer.decode(outputs[0], skip_special_tokens=True)
    return compressed

def compressibility(text: str, similarity_threshold: float):
    original_embedding = embedder.encode(text)
    ratios = np.arange(0.99, 0, -0.01)
    good_ratios = []
    for ratio in ratios:
        compressed = compress(text, ratio)
        compressed_embedding = embedder.encode(compressed)
        similarity = cosine_similarity([original_embedding], [compressed_embedding])[0][0]
        if similarity >= similarity_threshold: #for the comments it would be <=
            #return round(ratio + 0.01, 2)
            good_ratios.append(round(ratio, 2))
        print(round(ratio, 2), similarity)
    return good_ratios
    #return 0.0

'''
def extract_propositions_allennlp(text: str):
    propositions = []
    sentences = nltk.sent_tokenize(text)
    for sentence in sentences:
        result = srl_predictor.predict(sentence=sentence)
        #result gives result['words'], which is a list of tokens,
        #and result['verbs'], which is a list of predicate dictionaries.
        #each predicate dictionary has a 'verb' field, which is the predicate,
        #a 'tags' field, which is a list of tags, and a 'description' field,
        #which is a single string. 
        words, verbs = result['words'], result['verbs']
        for verb_dict in verbs:
            verb, tags = verb_dict['verb'], verb_dict['tags']
            args = defaultdict(list) #automatically initializes with empty lists
            current_arg = None
            for token, tag in zip(words, tags): 
                if tag.startswith('B-ARG'): #B-ARGi is beginning of argument i
                    current_arg = tag[2:] #labels as argument i
                    args[current_arg].append(token)
                elif tag.startswith('I-ARG') and current_arg: #I-ARGi is inside argument i
                    #this assumes that the arguments are contiguous, which is true - 
                    #if one argument i is split across two sentences, it will get two B-ARGi tags.
                    args[current_arg].append(token)
                else:
                    current_arg = None
            prop = {'verb': verb}
            for arg_label, token_list in args.items(): #arg_label is arg0, arg1, etc
                prop[arg_label] = ' '.join(token_list) #turn from list to string
            propositions.append(prop)
    #remove duplicates
    unique_propositions = {frozenset(prop.items()) for prop in propositions}
    return list(unique_propositions)

#this is the better version but I don't fully understand it yet so keeping both
def extract_propositions_2(text: str):
    propositions = []
    sentences = nltk.sent_tokenize(text)
    for sentence in sentences:
        result = srl_predictor.predict(sentence=sentence)
        for verb_info in result['verbs']:
            description = verb_info['description']
            arg_strings = re.findall(r"\[([A-Z\-0-9]+):\s+([^\]]+)\]", description)
            prop = {}
            for role, chunk in arg_strings:
                if role == 'V':
                    prop["verb_phrase"] = chunk
                else:
                    prop[role] = chunk
            propositions.append(prop)
        unique = {tuple(sorted(s.items())) for s in propositions}
    return [dict(s) for s in list(unique)]




def proposition_density(text: str):
    propositions = extract_propositions_allennlp(text)
    unique_propositions = set(propositions)
    density = len(unique_propositions) / len(text.split())
    return density, list(unique_propositions)
'''

if __name__ == "__main__":
    #cleanup_files()
    #if you want line breaks, you need to format it this way 
    # rather than with triple quotes, for token reasons
    
    sample = ( 
        "Dear local newspaper, I think effects computers have on people are great learning skills/affects because they give us time to chat with friends/new people, helps us learn about the globe(astronomy) and keeps us out of troble! Thing about! Dont you think so? How would you feel if your teenager is always on the phone with friends! Do you ever time to chat with your friends or buisness partner about things. Well now - there's a new way to chat the computer, theirs plenty of sites on the internet to do so: @ORGANIZATION1, @ORGANIZATION2, @CAPS1, facebook, myspace ect. Just think now while your setting up meeting with your boss on the computer, your teenager is having fun on the phone not rushing to get off cause you want to use it. How did you learn about other countrys/states outside of yours? Well I have by computer/internet, it's a new way to learn about what going on in our time! You might think your child spends a lot of time on the computer, but ask them so question about the economy, sea floor spreading or even about the @DATE1's you'll be surprise at how much he/she knows. Believe it or not the computer is much interesting then in class all day reading out of books. If your child is home on your computer or at a local library, it's better than being out with friends being fresh, or being perpressured to doing something they know isnt right. You might not know where your child is, @CAPS2 forbidde in a hospital bed because of a drive-by. Rather than your child on the computer learning, chatting or just playing games, safe and sound in your home or community place. Now I hope you have reached a point to understand and agree with me, because computers can have great effects on you or child because it gives us time to chat with friends/new people, helps us learn about the globe and believe or not keeps us out of troble. Thank you for listening."
    )
    #total_bits, per_token_bits = info_content(sample)
    print(sample)
    print(f"Character count: {len(sample)}")
    #print(f"Total tokens: {total_bits / per_token_bits}")
    #print(f"Total bits: {total_bits:.2f}")
    #print(f"Bits per token: {per_token_bits:.2f}")

    #print the 0.99 compression
    print(f"Compressed by 0.99: {compress(sample, 0.99)}")
    ratios = compressibility(sample, 0.9)
    print(f"Compressible by {min(ratios)}")
    #print(f"Good compressibility ratios: {compressibility(sample, 0.9)}")
    #print(f"Compressed by 0.36: {compress(sample, 0.36)}. with similarity {cosine_similarity([embedder.encode(sample)], [embedder.encode(compress(sample, 0.36))])[0][0]}")
    '''density, propositions = proposition_density(sample)
    print(f"Proposition density: {density} per word. {len(propositions)} propositions, {len(sample.split())} words.")
    for prop in propositions:
        print(prop)
    for prop in extract_propositions_2(sample):
        print(prop)
'''

