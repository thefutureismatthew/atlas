

from foundations_spec import *
from contextlib import contextmanager
from acceptance.mixins.run_local_job import RunLocalJob
from acceptance.mixins.run_with_default_foundations_home import RunWithDefaultFoundationsHome

class TestResultJobBundle(Spec, RunLocalJob, RunWithDefaultFoundationsHome):
    @set_up
    def set_up(self):
        import subprocess
        import os

        with self.unset_foundations_home():
            subprocess.run(f'python -m foundations login http://{os.getenv("LOCAL_DOCKER_SCHEDULER_HOST", "localhost")}:5558 -u test -p test'.split(' '))

    def test_local_run_job_bundle_is_same_as_remote(self):
        import os
        from foundations_contrib.utils import foundations_home
        import tarfile
        from acceptance.mixins.run_process import run_process
        from foundations_contrib.global_state import redis_connection
        import foundations

        self._deploy_job_file('acceptance/fixtures/run_locally')            
        local_job_id = redis_connection.get('foundations_testing_job_id').decode()

        with self.unset_foundations_home():
            remote_job = foundations.submit(job_directory='acceptance/fixtures/run_locally', command=['main.py'], num_gpus=0)
            remote_job.wait_for_deployment_to_complete()
            # Please forgive this hackery; we currently don't have an official way of getting archives through the SDK
            remote_job._deployment.get_job_archive()

        root_archive_directory = os.path.expanduser(f'{foundations_home()}/job_data/archive')
        local_archive_directory = f'{root_archive_directory}/{local_job_id}/artifacts/'
        local_files = set(os.listdir(local_archive_directory))

        job_id = remote_job.job_name()
        job_id_prefix = f'{job_id}/'
        tar_file_name = f'{job_id}.tgz'

        tar = tarfile.open(tar_file_name)
        remote_files = set([name[len(job_id_prefix):] for name in tar.getnames() if name.startswith(job_id_prefix)])
        tar.close()

        try:
            os.remove(tar_file_name)
        except OSError:
            pass

        # Assert subset because the remote files actually contains an additional file generated by the job submission process
        self.assertTrue(local_files.issubset(remote_files))