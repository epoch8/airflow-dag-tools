# Airflow DAG Tools

Usefull tools to manage DAGs in Airflow

Currently added tools:
1. Rebind DAG history from one DAG to another
2. Hide DAG from web panel

## Screenshots

<img src="https://user-images.githubusercontent.com/7437894/48622460-e714ff00-e9b7-11e8-8231-4e451c18a0e3.png" height="400" width="600"/>

## Install

Switch to the root of your Airflow project.

```sh
git clone https://github.com/epoch8/airflow-dag-tools plugins/airflow-dag-tools
```

That's it. You're done.

## Docker Install

If you use airflow in docker you can simply modify your Dockerfile like this:

```sh
RUN cd ${AIRFLOW_HOME}/plugins && \
    wget https://github.com/epoch8/airflow-dag-tools/archive/${AIRFLOW_DAG_TOOLS_VERSION}.tar.gz -O airflow-dag-tools-${AIRFLOW_DAG_TOOLS_VERSION}.tar.gz && \
    tar zxf airflow-dag-tools-${AIRFLOW_DAG_TOOLS_VERSION}.tar.gz
```

## Usage

All tools available at Admin tab in Airflow web server


## License

Distributed under the BSD license. See [LICENSE](LICENSE) for more
information.
