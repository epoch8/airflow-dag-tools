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


class BindDAGsHistory(BaseView):

    @staticmethod
    @provide_session
    def get_available_dags(session=None):
        dagbag = DagBag(DAGS_FOLDER)
        orm_dags = [x[0] for x in session.query(DagModel.dag_id).filter(DagModel.is_paused.is_(True)).all()]

        old_dags_with_task_history = [x[0] for x in session.query(TaskInstance.dag_id).filter(
            TaskInstance.state.notin_([State.RUNNING])).filter(
            TaskInstance.dag_id.in_(orm_dags)).distinct().all()]

        webserver_dags = [dag for dag in dagbag.dags.values() if not dag.parent_dag]

        new_dags_for_task_history = [dag.dag_id for dag in webserver_dags]
        return {
            'old_dags_with_task_history': old_dags_with_task_history,
            'new_dags_for_task_history': new_dags_for_task_history,
        }

    @staticmethod
    @provide_session
    def rebind_history(old_dag_id: str, new_dag_id: str, session=None, drop_old_dag='True'):

        session.query(DagRun).filter(DagRun.dag_id == old_dag_id).update({DagRun.dag_id: new_dag_id})
        session.query(DagStat).filter(DagStat.dag_id == old_dag_id).update({DagStat.dag_id: new_dag_id})
        session.query(SlaMiss).filter(SlaMiss.dag_id == old_dag_id).update({SlaMiss.dag_id: new_dag_id})

        session.query(TaskInstance).filter(TaskInstance.dag_id == old_dag_id).update({TaskInstance.dag_id: new_dag_id})
        session.query(TaskFail).filter(TaskFail.dag_id == old_dag_id).update({TaskFail.dag_id: new_dag_id})
        session.query(XCom).filter(XCom.dag_id == old_dag_id).update({XCom.dag_id: new_dag_id})
        session.query(BaseJob).filter(BaseJob.dag_id == old_dag_id).update({BaseJob.dag_id: new_dag_id})
        session.query(Log).filter(Log.dag_id == old_dag_id).update({Log.dag_id: new_dag_id})

        logpath = os.path.expanduser(conf.get('core', 'BASE_LOG_FOLDER'))
        logpath_old_dag = os.path.join(logpath, old_dag_id)
        logpath_new_dag = os.path.join(logpath, new_dag_id)

        if os.path.isdir(logpath_old_dag) and os.path.isdir(logpath_new_dag):
            files = os.listdir(logpath_old_dag)
            for f in files:
                shutil.move(logpath_old_dag + f, logpath_new_dag)

        elif os.path.isdir(logpath_old_dag) and not os.path.isdir(logpath_new_dag):
            os.rename(logpath_old_dag, logpath_new_dag)

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

    @expose('/', methods=['GET', 'POST'])
    @wwwutils.action_logging
    def view(self):
        airflow_version = airflow.__version__

        old_dag_id = 'Select'
        new_dag_id = 'Select'
        agreement_with_change = 'False'
        old_dag_stats = None
        new_dag_stats = None
        show_sumbit_btn = 'False'
        drop_old_dag = 'True'

        if request.method == 'POST':
            old_dag_id = request.form.get('old_dag_id', default='Select')
            new_dag_id = request.form.get('new_dag_id', default='Select')
            agreement_with_change = request.form.get('agreement_with_change', default="False")

            if old_dag_id != 'Select' and new_dag_id != 'Select':
                show_sumbit_btn = 'True'

            if request.form['action'] == 'Bind DAG history':
                if agreement_with_change == "True":
                    self.rebind_history(old_dag_id=old_dag_id, new_dag_id=new_dag_id, drop_old_dag=drop_old_dag)

                    show_sumbit_btn = 'False'
                    agreement_with_change = 'False'

        if old_dag_id != 'Select':
            old_dag_stats = self.dag_staistics(old_dag_id)
        if new_dag_id != 'Select':
            new_dag_stats = self.dag_staistics(new_dag_id)

        dags = self.get_available_dags()
        return self.render(
            'airflow_rebind_dag_history/airflow_rebind_dag_history.html',
            airflow_version=airflow_version,
            old_dags_with_task_history=dags['old_dags_with_task_history'],
            new_dags_for_task_history=dags['new_dags_for_task_history'],
            old_dag_id=old_dag_id,
            new_dag_id=new_dag_id,
            agreement_with_change=agreement_with_change,
            old_dag_stats=old_dag_stats,
            new_dag_stats=new_dag_stats,
            show_sumbit_btn=show_sumbit_btn,
            drop_old_dag=drop_old_dag
        )


ADMIN_VIEW = BindDAGsHistory(category="Admin", name="Bind DAGs History")

bp = Blueprint(
    "airflow_rebind_dag_history",
    __name__,
    template_folder='templates',  # registers airflow/plugins/templates as a Jinja template folder
    static_folder='static',
    static_url_path='/static/')


class AirflowRenamePlugins(AirflowPlugin):
    name = "airflow_rebind_dag_history_plugin"
    operators = []
    hooks = []
    executors = []
    macros = []
    admin_views = [ADMIN_VIEW]
    flask_blueprints = [bp]
    menu_links = []
