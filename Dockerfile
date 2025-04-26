
FROM quay.io/jupyter/base-notebook:lab-4.3.4
USER root

RUN conda install -c conda-forge \
    conda-forge::jupyter_scheduler \
    matplotlib \
    scikit-learn \
    psycopg2-binary \
    pandas \
    wheel \
    nodejs 
    
RUN pip install --no-cache-dir mitosheet nbdev ipython-sql
RUN jupyter labextension enable mitosheet

# copy and install jupyter-finance
COPY ./dist/*.tar.gz ./latest.tar.gz
RUN pip install ./latest.tar.gz

# copy all notebooks to container
COPY ./nbs/0*.ipynb /home/jovyan/work
RUN chmod -R 777 /home/jovyan/work

WORKDIR /home/jovyan/work
EXPOSE 8888
USER ${NB_UID}
