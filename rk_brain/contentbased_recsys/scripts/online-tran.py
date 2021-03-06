import logging
import random
import pandas as pd
from gensim import models, corpora, similarities
import time
from multiprocessing import Pool
from gensim.models.doc2vec import Doc2Vec,TaggedDocument
from rk_brain.contentbased_recsys.scripts.clean_metadata import clean_df, parallelize_dataframe
from collections import namedtuple
# For log Information 
logging.basicConfig(
    format='%(asctime)s : %(threadName)s : %(levelname)s : %(message)s',
    level=logging.DEBUG,
)



model = Doc2Vec.load("../model/final_model")
arxiv_id_tags = model.docvecs.doctags




print("Connected with Database")
query = "SELECT arxiv_id, title, abstract FROM arxivOverload.METADATA"
metadata_table = pd.read_sql(query, con=connection)
print("loaded from database")
start = time.time()

data = parallelize_dataframe(metadata_table, clean_df)
end = time.time()
print("completed cleaning in:",end-start)

def Doc2vec_traning(dataframe):
    tagged_docs = []
    analyzedDocument = namedtuple('AnalyzedDocument', 'words tags')
    for text, tags in zip(dataframe['tokenized'].tolist(), dataframe['arxiv_id'].tolist()):
        tags = [tags]
        tagged_docs.append(analyzedDocument(text, tags))
    model = Doc2Vec( size = 400 # Model initialization
        , window = 50
        , min_count = 1
        , workers = 4)
    model.build_vocab(tagged_docs) # Building vocabulary
    alpha_val = 0.025        # Initial learning rate
    min_alpha_val = 1e-4     # Minimum for linear learning rate decay
    passes = 15              # Number of passes of one document during training
    alpha_delta = (alpha_val - min_alpha_val) / (passes - 1)

    for epoch in range(passes):

        # Shuffling gets better results

        random.shuffle(tagged_docs)

        # Train

        model.alpha, model.min_alpha = alpha_val, alpha_val

        model.train(tagged_docs, total_examples=model.corpus_count, epochs=model.epochs)

        # Logs

        print('Completed pass %i at alpha %f' % (epoch + 1, alpha_val))

        # Next run alpha

        alpha_val -= alpha_delta

    model.save("./model/")
    print("Model Saved into Disk")
    return model

def predict_similar(model, dataframe):
    main_list=[]
    for i in dataframe["arxiv_id"]:
        data = {}
        arxiv_list = []
        similarity = model.docvecs.most_similar(i, topn=1000)
        for j , k in similarity:
            arxiv_list.append(j)
        data["arxiv_id"] = i
        data["similar_papers"] = json.dumps(arxiv_list)
        main_list.append(data)        
    df = pd.DataFrame(main_list)
    df.to_csv("../outputs/"+"predections"+".csv", index=False)
    print("Saved prediction to models folder")

re_model = Doc2vec_traning(data)
print("-- Updated model")
print("Vocabulary length:", len(re_model.wv.vocab))
print()
predict_similar(model, data)








