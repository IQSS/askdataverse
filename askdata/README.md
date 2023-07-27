# Askdata

Experimental code to query tabular data with natural language queries.
The code takes the input natural language query, transforms it into a SQL query, executes the query on the database and then tries to translate the resul back into natural language. 

The code is meant not have memory, so each query is independent. This is a feature!

It exploits [LangChain](https://www.langchain.com) agents for the scope and [OpenAI](https://openai.com).

Requires an [OpenAI](https://openai.com) `key` to run (see code).

In the near future the underlying LLM model will be replaced by other models.

If you already use another large language model, as long as it is supported
by [LangChain](https://www.langchain.com), the code requires no modification.

We plan to expand the functionalities of this tool.

## Known issues:
* can generate hallucinations
* can be stuck into a loop that lead to no aswer or error
* there is no control over long queries, so the code may return an error
* the generated SQL query can be too large for the context window of the LLM

## Plans:
* fix some of the above issues
* add basic statical analysis functionalities
* add basic plotting functionalities

## To deploy on [shinyapps.io](https://www.shinyapps.io)
At present ShinyApps.io supports only python 3.10 so make sure your local environment is based on this release.

Hint: you can create an environment after installing [Anaconda](https://docs.anaconda.com/free/anaconda/install/index.html) with 

`conda create -n shinyapp python=3.10`

`conda activate shinyapp`
* adjust the variables `inputUrl` and `OPENAI_API_KEY` in the [app.py](app.py) file to your needs
* create a free account at [shinyapps.io](https://www.shinyapps.io)
* install the [application token](https://docs.posit.co/shinyapps.io/getting-started.html) 
* run the ["install certificates.command"](https://www.geeksforgeeks.org/how-to-install-and-use-ssl-certificate-in-python/) for your python version
* run `pip install -r requirements.txt`
* in your shell type: `export CONNECT_REQUEST_TIMEOUT=36000` and the return key. You can use a larger number if `rsconnect` fails due to a timeout error. This is a `shinyapps.io` issue
* deploy with: `rsconnect deploy shiny ./ --name askdataverse --title askdata --exclude *.db`



## Usage 
This script requires two arguments: `fileId` and `siteUrl`. 
The parameter `dataset_pid` is collected but not yet used.

* for Harvard Dataverse `siteUrl` always equals to [https://dataverse.harvard.edu](https://dataverse.harvard.edu)
* `fileId` is the internal identifier in the Dataverse database

### Examples:
* Example 1: [https://askdataverse.shinyapps.io/askdata/?fileid=4862482&siteUrl=https://dataverse.harvard.edu](https://askdataverse.shinyapps.io/askdata/?fileid=4862482&siteUrl=https://dataverse.harvard.edu)


or, if run locally (replace `64504` with your port):
* [http://localhost:64504/?fileid=4862482&siteUrl=https://dataverse.harvard.edu](http://localhost:64504/?fileid=4862482&siteUrl=https://dataverse.harvard.edu)

* Example 2: [https://askdataverse.shinyapps.io/askdata/?fileid=4458512&siteUrl=https://dataverse.harvard.edu](https://askdataverse.shinyapps.io/askdata/?fileid=4458512&siteUrl=https://dataverse.harvard.edu)
  
### Questions:
* what is this data about? (this is the default starting question)
* what's the most interesting thing about this data?
* surprise me with this data (this is a risky question, but helps to understand the limits of this tool)


and in particular, if you use the data from Example 1 in the above:
* do males smoke more than women?
* what is the average age of smokers by city?
* where people smoke the most?


and if you use the data from Example 2 in the above:
* how many people died by covid?
* did females recovered more than males?


etc, the limit is your creativity!

Enjoy!
