import math
import torch
from transformers import GPT2LMHeadModel, GPT2TokenizerFast
#why fast?

#don't know what this is
tokenizer = GPT2TokenizerFast.from_pretrained('gpt2')
model = GPT2LMHeadModel.from_pretrained('gpt2')
model.eval()

#helper to get the probability of a token given the history
@torch.no_grad()
def q_prob(token_id: int, history_ids: torch.Tensor) -> float:
    #token_id is the id of the token to predict
    #history_ids is a list (1xT tensor) of the history of tokens
    #return the probability of the token

    outputs = model(history_ids)
    logits = outputs.logits #shape (1, T, V)
    last_logits = logits[0, -1, :] #shape (V,)
    log_probs = torch.log_softmax(last_logits, dim=-1)
    return float(torch.exp(log_probs[token_id]))

#tokenizes the text then computes the entropy bits
def entropy_bits(text: str):
    enc = tokenizer(text, return_tensors='pt')
    ids = enc.input_ids[0] #Shape (N,)
    total_bits = 0.0
    for i in range(1,len(ids)):
        history_ids = ids[:i].unsqueeze(0) #Shape (1,i)
        p_next = q_prob(int(ids[i]), history_ids)
        if p_next <= 0:
            raise ValueError(f"Invalid probability: {tokenizer.decode(ids[i])}")
        total_bits += -math.log2(p_next)
    return total_bits, total_bits/(len(ids) - 1) #why -1?


if __name__ == "__main__":
    #if you want line breaks, you need to format it this way 
    # rather than with triple quotes, for token reasons
    sample = ( 
        "Machines are embedded in art so deeply that we don’t even really notice them. Most writers don’t think it’s a perversion of their work to type it on a computer. Even the most conservative likely doesn’t deactivate the spell check built into Google Docs or Microsoft Word. But that same writer probably rebukes ChatGPT and regards AI-produced writing as second class, in hypotheticals and when they can spot it. They complain with their friends and at conferences about how it makes bad content and defiles the craft and yet is slowly but surely displacing creators in their industry. Fundamentally, a lot of artists don’t regard AI-generated art as art. Some instances of engineering in art are acceptable, though; they might defend the honor of an artist who uses a tool like Procreate to create animations and drawings. They admire the daring of a readymade sculpture."
    )
    total_bits, per_token_bits = entropy_bits(sample)
    print(sample)
    print(f"Character count: {len(sample)}")
    print(f"Total tokens: {total_bits / per_token_bits}")
    print(f"Total bits: {total_bits:.2f}")
    print(f"Bits per token: {per_token_bits:.2f}")
