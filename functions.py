import pandas as pd
import bz2
import os
import numpy as np
import time
import spacy
import glob
import matplotlib.pyplot as plt
from nltk.sentiment.vader import SentimentIntensityAnalyzer

def chunkify(filepath, chunk_size, outputname, timing=False):
    """
    This function chunk quotebank files to multiple smaller files. 
    
    INPUTS: 
    filepath: path of quotebank file to chunk. 
    chunk_size: (int) it is a row number where the file will be chuncked at
    outputname: is what every output chunk starts their name as
    timing:  is per chunk for benchmarks
    """
    batch_no = 1
    for chunk in pd.read_json(filepath, chunksize=chunk_size, lines=True, compression='bz2'):
        # Taking the time of loading each chunk
        if timing:
            before = time.time()

        output = 'Data/' + outputname + '-' + str(batch_no) + '.csv'

        chunk.to_csv(output, index=False)

        compression_level = 9
        # Source file for bz2 comrpession
        source_file = output
        destination_file = output + '.bz2'

        with open(source_file, 'rb') as data:
            # Reads the content of the file and makes a compressed copy
            compressed = bz2.compress(data.read(), compression_level)
        fh = open(destination_file, "wb")
        # Make a new compressed file with compressed content
        fh.write(compressed)
        fh.close()

        # Removes the .csv file to save space
        os.remove(output)

        if timing:
            after = time.time()
            print(after - before, 's')

        batch_no += 1

def find_csv_filenames(path_to_dir, year):
    """
    Finds all chunkfiles that belongs to a given year and is in a given directory
    """
    filenames = os.listdir(path_to_dir)
    return [filename for filename in filenames if filename.startswith("quotes-" + str(year) + "-")]    

def get_quotes(speaker, year, timing=False):
    """
    returns the dataset with only quotes from the given speaker from the files of a given year
    timing for the whole function for benchmarks
    """
    if timing:
        before = time.time()

    cd = 'Data/' # Set working directory
    filenames = find_csv_filenames(cd, year) #Get chunks from a given year
    file_arr = np.array(filenames) # change list to numpy array
    N = len(filenames) #Number of chunks
    df1 = pd.read_csv(cd + file_arr[0]) # load first chunk
    df_all = df1[df1["speaker"]==speaker] # Extract elon musk quotes from first chunk file
    # For loop through all chunks and concat data frames to have one data frame with all elon musk quotes
    for i in range(1,N):
        name_2load = cd + file_arr[i]
        current_df = pd.read_csv(name_2load)
        df_elo_current = current_df[current_df["speaker"]==speaker]
        df_all = pd.concat([df_all, df_elo_current], axis=0)

    if timing:
        after = time.time()
        print(after - before, 's')

    return df_all

def make_csv(dataFrame, speaker, year, compression='bz2'):
    """
    create a compressed csv of a dataframe of quotes for a speaker and a year
    """
    dataFrame.to_csv('Data/' + speaker + '-quotes-' + str(year) + '.csv.' + compression, index=False)

def combining_yearly_quotes(speaker):
    """
    takes all the quote-files for a given speaker (each year) and combines them into a new single file
    """
    # Load all of the speakers quotes of all years
    path = 'Data/'
    # The speakers data in Data/ should be 'SPEAKER-quotes-YEAR.csv.bz2'
    # This will only grab files starting with the speaker's name
    all_files = glob.glob(path + speaker +"*.bz2")

    # Combine all speakers quotes from all the years 
    li = []
    for filename in all_files:
        df = pd.read_csv(filename)
        li.append(df)

    # Combines all the dataframes
    frame = pd.concat(li, axis=0, ignore_index=True)

    frame.to_csv(path + 'all-' + speaker + '-quotes.csv.bz2', compression='bz2', index=False)

def high_probability_quotes(df, cutoff):
    """
    drops all quotes that don't have the main speaker's probability higher than the cutoff
    """
    # Creates a new column with the speakers probability as a float
    df['probasE'] = df['probas'].str.extract(r'([\d][.][\d]*)').astype('float')
    # Returns the rows with a value over the cutoff
    return df[df['probasE'] >= cutoff]

def create_org_df(spacy_model, df, timing=False):
    """
    create a dataframe with the organizations from the quotes in a dataframe
    timing for the whole function including loading spacy_model
    """
    if timing:
        before = time.time()

    spacy_nlp = spacy.load(spacy_model)

    #gets filled with dictionaries for rows
    quote_list = []

    for i in range(0, df.shape[0]):
        quote = df.iloc[i]['quotation']
        # Extracts the quote and looks at it with nlp
        doc = spacy_nlp(quote)

        for element in doc.ents:
            # If a token gets categorized as ORG then it makes a dictionary for quote_list
            if element.label_ == 'ORG':
                quote_list.append({
                    # Adds the the organization as text (to avoid problems with object not loading from memory)
                    'ORG' : element.text,
                    'date' : df.iloc[i]['date'],
                    'numOccurrences' : df.iloc[i]['numOccurrences'],
                    'quotation' : df.iloc[i]['quotation'],
                    'quoteID' : df.iloc[i]['quoteID'],
                    'probas' : df.iloc[i]['probas']})

    # Turns quote_list into a DataFrame with keys as columns
    org_df = pd.DataFrame.from_dict(quote_list)
    # Some quotes mention the same company multiple times, which results in duplicate rows for this df. (ca. 700 on 0 cutoff)
    org_df = org_df.drop_duplicates()

    if timing:
        after = time.time()
        print(after - before, 's')

    return org_df

def plot_by_org (df, organisation):
    """
    Plots how many times a company is mentioned for each year.
    """
    df = df[df['ORG'] == organisation]
    quotes_per_year = df.groupby(['year']).size()
    quotes_per_year.plot.bar()
    plt.xlabel("Years")
    plt.ylabel("Number of quotes of Elon Musk about" + organisation)
    plt.show()

    
def add_polarity_score_to_df(df):
    """
    This function takes in the dataframe with quotations and then add to it a column 'Score' that has the compound score from the Sentiment analysis, which is a text analysis method that detects polarity. So the score here is the compound polairty score of the quote
    ---------------------------------------------------------
    INPUTS: 
    
    df:     Data frame with quotes.
    ---------------------------------------------------------
    OUTPUTS: 
    
    df_copy: Data frame with quotes and polarity score.
    ---------------------------------------------------------
    Warning: This function require you to have run the following command "nltk.download('vader_lexicon')"
    """
    sid = SentimentIntensityAnalyzer()
    
    df_copy = df.copy()
    df_copy['sentiment'] = df_copy['quotation'].apply(lambda quotation: sid.polarity_scores(quotation)['compound'])
    return df_copy

def add_sentiment_category(df, neg_treshhold, pos_treshhold):
    """
    This function takes in the dataframe with polarity(sentiment) score and add a column 'sentiment_category'
    ---------------------------------------------------------
    INPUTS: 
    
    df:     Data frame with sentiment scores.
    neg_treshhold: the threshhold for a value to be categorized as negative
    pos_treshhold: the threshhold for a value to be categorized as positive
    ---------------------------------------------------------
    OUTPUTS: 
    
    df_copy: Data frame with added column 'sentiment_category'.
    ---------------------------------------------------------
    """
    def categorize(score):
        if score <= neg_treshhold:
            return -1
        elif score >= pos_treshhold:
            return 1
        else:
            return 0
    
    df_copy = df.copy()
    df_copy['sentiment_category'] = df_copy['sentiment'].apply(lambda s: categorize(s))
    return df_copy