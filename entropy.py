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
    sample = "The federal government will continue to hold Mahmoud Khalil, SIPA ’24, in an Immigration and Customs Enforcement facility in Louisiana, arguing that a Wednesday court order declaring Khalil’s detainment unlawful “does not interfere” with the government’s “authority to detain Khalil on other grounds,” a Department of Justice letter reads. U.S. District Judge Michael Farbiarz set a 1:30 p.m. Friday deadline for the federal government to appeal the court ruling that Khalil cannot be detained under the rarely invoked legal provision cited by Secretary of State Marco Rubio in Khalil’s detention. The government sent a letter to Farbiarz, outlining its argument after the 1:30 p.m. deadline had elapsed."
    total_bits, per_token_bits = entropy_bits(sample)
    print(f"Total bits: {total_bits:.2f}")
    print(f"Bits per token: {per_token_bits:.2f}")
