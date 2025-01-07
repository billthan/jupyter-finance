FROM postgres:17.2

ENV POSTGRES_DB=finances

COPY ./init.sql /docker-entrypoint-initdb.d/init.sql
EXPOSE 5432

CMD ["docker-entrypoint.sh", "postgres"]
