import pandas as pd
from tqdm import tqdm
tqdm.pandas() #progress bar for pandas 
import entropy
import matplotlib.pyplot as plt
import seaborn as sns
from scipy.stats import spearmanr, pearsonr


#read in the training set
#quoting=3 leaves the quotes alone
path = "asap-aes/training_set_rel3.tsv"
df = pd.read_csv(path, sep="\t", quoting=3, encoding="latin-1").head(1000)

#important columns
ESSAY_COL = "essay"
SCORE_COL = "domain1_score"
SET_COL = "essay_set"

def compute_features(text: str):
    _, bits_per_token = entropy.info_content(text)
    #compressibility = entropy.compressibility(text, 0.9)
    #prop_density, _ = entropy.proposition_density(text)
    return pd.Series({
        "bits_per_token": bits_per_token
        #"compressibility": compressibility
        #"prop_density": prop_density #commented out for dependency issues
    })

# apply the function and add the results to the dataframe
feature_df= df[ESSAY_COL].progress_apply(compute_features)
df = pd.concat([df, feature_df], axis=1)

#scatterplots for each feature
for col in ["bits_per_token"]: #"compressibility", "prop_density"]:
    g = sns.relplot(
        data=df, x=col, y=SCORE_COL, hue=SET_COL, 
        height=4, aspect=1.2, kind="scatter", alpha=0.4
    )
    g.figure.suptitle(f"{col} vs human score", y=1.02) 
    plt.show()
    