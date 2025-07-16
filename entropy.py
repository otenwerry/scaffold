import math
import torch
import torch.nn.functional as F
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

#computes the bits of information content in a string of english text
def info_content(text: str, device="cpu"):
    #tokenize the text
    enc = tokenizer(text, return_tensors='pt')
    ids = enc.input_ids.to(device)
    with torch.no_grad():#disables gradient tracking to save memory
        #get the logits of all tokens in the text
        logits = model(ids).logits
    #get the log probabilities of all tokens. compute along the last dimension (vocabulary)
    log_probs = F.log_softmax(logits, dim=-1)
    shifted_log_probs = log_probs[0, :-1, :] #discard the last token (no next token)
    targets = ids[0, 1:] #discard the first token (no history)
    #get the log probabilities of the next tokens
    token_log_probs = shifted_log_probs[torch.arange(targets.size(0)), targets]
    #convert to bits
    bits = -token_log_probs / math.log(2)
    #sum the bits and divide by the number of tokens to get the average bits per token
    total_bits = bits.sum().item()
    avg_bits = total_bits / bits.size(0)
    return total_bits, avg_bits


'''
questions
is torch.nn.functional better than torch for log softmax or can I use torch.log_softmax and not import F?
what is the vocabulary dimension in the logits? 
how does the token_log_probs work? i understand why we're discarding the first and last tokens, but how does the shifting happen and how does the actual calculation work?
is the bits calculation done that way for numerical reasons or can I just do log2(exp(token_log_probs))? actually maybe that doesn't make it simpler.

'''

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
        #"There is currently a lively, ongoing controversy among many sociologists and other professionals who study human nature : theories are being spun and arguments are being conducted among them about what it means that so many young people—and older people, for that matter—who live in our society today are so very interested in stories about zombies.?"
    )
    total_bits, per_token_bits = info_content(sample)
    print(sample)
    print(f"Character count: {len(sample)}")
    print(f"Total tokens: {total_bits / per_token_bits}")
    print(f"Total bits: {total_bits:.2f}")
    print(f"Bits per token: {per_token_bits:.2f}")

    #print the 0.99 compression
    '''print(f"Compressed by 0.99: {compress(sample, 0.99)}")
    ratios = compressibility(sample, 0.9)
    print(f"Compressible by {min(ratios)}")'''
    #print(f"Good compressibility ratios: {compressibility(sample, 0.9)}")
    #print(f"Compressed by 0.36: {compress(sample, 0.36)}. with similarity {cosine_similarity([embedder.encode(sample)], [embedder.encode(compress(sample, 0.36))])[0][0]}")
    '''density, propositions = proposition_density(sample)
    print(f"Proposition density: {density} per word. {len(propositions)} propositions, {len(sample.split())} words.")
    for prop in propositions:
        print(prop)
    for prop in extract_propositions_2(sample):
        print(prop)
'''

