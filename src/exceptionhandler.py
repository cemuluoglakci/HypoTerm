import shlex, subprocess

class ExceptionHandler():
    def __init__(self):
        self.singularity_start_command = "singularity instance start --bind models:/root/.ollama  ollama_latest.sif ollama"
        self.singularity_stop_command = "singularity instance stop ollama"
        self.singularity_serve_command = "singularity exec instance://ollama ollama serve"

    def restart_ollama_container(self):
        stop_results = subprocess.run(self.singularity_stop_command, shell=True, universal_newlines=True, check=True)
        print(stop_results)

        start_results = subprocess.run(self.singularity_start_command, shell=True, universal_newlines=True, check=True)
        print(start_results)

        serve_args = shlex.split(self.singularity_serve_command)
        serve_results = subprocess.Popen(serve_args)
        print('result returned')
        print(serve_results)
