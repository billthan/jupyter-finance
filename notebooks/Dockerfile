
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
    
EXPOSE 8888
COPY ./*.ipynb /home/jovyan/work

RUN chmod -R 777 /home/jovyan/work



#USER ${NB_UID}
