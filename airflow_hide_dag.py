from flask import Blueprint, request
from flask_admin import BaseView, expose
import os
import shutil
import airflow
from airflow import configuration as conf
from airflow.plugins_manager import AirflowPlugin
from airflow.settings import DAGS_FOLDER
from airflow.utils.db import provide_session
from airflow.www import utils as wwwutils
from airflow.utils.state import State
from airflow.models import DagModel, DagRun, DagStat, Log, SlaMiss, TaskFail, TaskInstance, XCom, DagBag
from airflow.jobs import BaseJob


class HideDag(BaseView):

    @staticmethod
    @provide_session
    def get_available_dags(session=None):
        dagbag = DagBag(DAGS_FOLDER)
        webserver_dags = {dag_id: dag for dag_id, dag in dagbag.dags.items() if not dag.parent_dag}

        # orm_dags = [x for x in session.query(DagModel).all()]
        orm_dags = {x.dag_id: x for x in session.query(DagModel).all()}

        # dags = {dag.dag_id: dag.is_active for dag in orm_dags if dag.dag_id not in webserver_dags}
        return {'orm_dags': orm_dags, 'webserver_dags': webserver_dags}

    @staticmethod
    @provide_session
    def hide_dag(old_dag_id: str, new_dag_id: str, session=None, drop_old_dag='True'):



        if drop_old_dag == 'True':
            session.query(DagModel).filter(DagModel.dag_id == old_dag_id).delete()

        session.commit()
        return
    
    @staticmethod
    @provide_session
    def dag_staistics(dag_id: str, session=None):

        logpath = os.path.join(os.path.expanduser(conf.get('core', 'BASE_LOG_FOLDER')), dag_id)
        logdir_result = "LogDir doesn't exists"
        if os.path.exists(logpath) and os.path.isdir(logpath):
            dir_count = 0
            file_count = 0
            for _, dirs, files in os.walk(logpath):
                dir_count += len(dirs)
                file_count += len(files)
            logdir_result = 'Tasks - {0}, Log files - {1}'.format(dir_count, file_count)

        data = {
            'DagModel': session.query(DagModel).filter(DagModel.dag_id == dag_id).count(),
            'DagRun': session.query(DagRun).filter(DagRun.dag_id == dag_id).count(),
            'DagStat': session.query(DagStat).filter(DagStat.dag_id == dag_id).count(),
            'SlaMiss': session.query(SlaMiss).filter(SlaMiss.dag_id == dag_id).count(),
            'TaskInstance': session.query(TaskInstance).filter(TaskInstance.dag_id == dag_id).count(),
            'TaskFail': session.query(TaskFail).filter(TaskFail.dag_id == dag_id).count(),
            'XCom': session.query(XCom).filter(XCom.dag_id == dag_id).count(),
            'BaseJob': session.query(BaseJob).filter(BaseJob.dag_id == dag_id).count(),
            'Log': session.query(Log).filter(Log.dag_id == dag_id).count(),
            'LogFiles': logdir_result
        }
        return data

    @expose('/active', methods=['GET'])
    @provide_session
    @wwwutils.action_logging
    def paused(self, session=None):
        dag_id = request.args.get('dag_id')
        orm_dag = session.query(DagModel).filter(DagModel.dag_id == dag_id).first()
        if request.args.get('is_active') == 'false':
            orm_dag.is_active = False
        else:
            orm_dag.is_active = True
        session.merge(orm_dag)
        session.commit()
        return "OK"

    @expose('/', methods=['GET', 'POST'])
    @wwwutils.action_logging
    def view(self):
        airflow_version = airflow.__version__

        if request.method == 'POST':
            f = request.form
            for key in f.keys():
                for value in f.getlist(key):
                    print(key, ":", value)
            dag_id = "a"
            self.hide_dag(dag_id=dag_id)


        dags = self.get_available_dags()
        return self.render(
            'airflow_hide_dag/airflow_hide_dag.html',
            airflow_version=airflow_version,
            orm_dags=dags['orm_dags'],
            webserver_dags=dags['webserver_dags'],
            dag_ids_in_page=dags['orm_dags'],
        )


ADMIN_VIEW = HideDag(category="Admin", name="Hide DAG")

bp = Blueprint(
    "airflow_hide_dag",
    __name__,
    template_folder='templates',  # registers airflow/plugins/templates as a Jinja template folder
    static_folder='static',
    static_url_path='/static/')


class AirflowRenamePlugins(AirflowPlugin):
    name = "airflow_hide_dag"
    operators = []
    hooks = []
    executors = []
    macros = []
    admin_views = [ADMIN_VIEW]
    flask_blueprints = [bp]
    menu_links = []
