"""
Using langchains create a task to check the security
of a login form found at a specific web address

THIS IS DANGEROUS TO RUN

Uses the hydra cli program
https://www.cyberpunk.rs/password-cracker-thc-hydra
"""
import logging
import os
import sys
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from urllib.parse import urlparse

from langchain_core.tools import Tool
from langchain_community.tools import DuckDuckGoSearchRun, ReadFileTool, ShellTool, WriteFileTool
from langchain_community.utilities.google_search import GoogleSearchAPIWrapper
from langchain_community.vectorstores import FAISS, Redis
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from langchain_experimental.autonomous_agents import AutoGPT

from tools.stream_to_logger import StreamToLogger


@dataclass
class EnvironmentConfig:
    """Runtime configuration derived from environment variables."""

    openai_api_key: str
    redis_url: Optional[str]
    google_api_key: Optional[str]
    google_cse_id: Optional[str]
    openai_model: str = "gpt-4o-mini"

def _get_env_config() -> EnvironmentConfig:
    """Load configuration from the current environment with validation."""

    openai_api_key = os.getenv("OPENAI_API_KEY")
    if not openai_api_key:
        raise EnvironmentError(
            "OPENAI_API_KEY must be set to run the login checker."
        )

    return EnvironmentConfig(
        openai_api_key=openai_api_key,
        redis_url=os.getenv("REDIS_URL"),
        google_api_key=os.getenv("GOOGLE_API_KEY"),
        google_cse_id=os.getenv("GOOGLE_CSE_ID"),
        openai_model=os.getenv("OPENAI_MODEL_NAME", "gpt-4o-mini"),
    )


def _build_google_search_tool(config: EnvironmentConfig) -> Optional[Tool]:
    """Create a Google search tool if credentials are present."""

    if config.google_api_key and config.google_cse_id:
        wrapper = GoogleSearchAPIWrapper(
            google_api_key=config.google_api_key,
            google_cse_id=config.google_cse_id,
        )
        return Tool(
            name="search",
            func=wrapper.run,
            description=(
                "Useful for answering questions about current events. "
                "Ask targeted questions."
            ),
        )

    return None


def _build_shell_tool() -> Tool:
    shell = ShellTool()
    return Tool(
        name="bash",
        func=shell.run,
        description="Execute safe, non-interactive shell commands.",
    )


class LoginChecker:
    def __init__(self, http_url):
        self.config = _get_env_config()
        self.uuid = str(uuid.uuid4()).replace('-', '')

        self.autogpt_resp = ";_; failed"

        # prompt for the agent to use, will be a list
        data_path = os.path.abspath("tools/data/")
        logs_path = os.path.abspath("tools/logs/")
        # bin_path = os.path.abspath("tools/bin")

        self.http_url = http_url

        # setup logging
        self.logging_file_name = f"lc_runlog{datetime.now().strftime('%Y%m%d_%H%M')}_{self.uuid}.txt"
        self.logging_file_path =  f"{logs_path}/{self.logging_file_name}"
        self.summary_file_name = f"lc_security_report{datetime.now().strftime('%Y%m%d_%H%M')}_{self.uuid}.txt"
        self.summary_file_path = f"{logs_path}/{self.summary_file_name}"
        
        if not os.path.exists(logs_path):
            os.makedirs(logs_path)

        if not os.path.exists(self.logging_file_path):
            open(self.logging_file_path, "w").close()
        
        logging.basicConfig(
            filename=self.logging_file_path,
            level=logging.INFO,
            format="\n%(message)s\n")

        self.logging = logging.getLogger(__name__)
        
        self.tools = []

        google_search_tool = _build_google_search_tool(self.config)
        if google_search_tool:
            self.tools.append(google_search_tool)
        else:
            self.logging.info(
                "Google search credentials not provided; defaulting to DuckDuckGo search."
            )

        # PythonREPLTool(),
        # ShellTool(),
        self.tools.extend(
            [
                _build_shell_tool(),
                WriteFileTool(),
                ReadFileTool(),
                Tool(
                    name="search2",
                    func=DuckDuckGoSearchRun().run,
                    description=(
                        "Useful for questions about current events. "
                        "Prefer targeted queries and use when Google search is unavailable."
                    ),
                ),
            ]
        )

        self.embeddings = OpenAIEmbeddings()

        self.error_log_path = f"{logs_path}/lc_error{datetime.now().strftime('%Y%m%d_%H%M')}_{self.uuid}.txt"
        if not os.path.exists(self.error_log_path):
            open(self.error_log_path, 'w').close()

        self.info_log_path =  f"{logs_path}/lc_info{datetime.now().strftime('%Y%m%d_%H%M')}_{self.uuid}.txt"
        if not os.path.exists(self.info_log_path):
            open(self.info_log_path, "w").close()

        urlparts = urlparse(self.http_url)
        hostport = urlparts.netloc.split(":")
        if len(hostport) == 2:
            hydra_host = f"-s {hostport[1]} {hostport[0]}"
        else:
            hydra_host = f"{hostport[0]}"

        self.goals = [
            # f"Stay on task with your goals and don't get into a loop. If you are looping, break the loop and re-exam your goals that you have left",
            # f"Check {self.http_url} if it is a government, corporate or social network website by searching the web. Use search2 if search is hitting a quota limit. If the URL contains .gov or .org then it is government or corporate. If it is, stop all tasks and finish with reply \"Not legal to run prompt check on {self.http_url}. Its a government or corporate website!!\"",
            # f"Do a search on cyber security laws and understand what is legal or not to hack and not get in trouble. Use search2 if search is hitting a quota limit.",
            # f"Do a search on what {self.http_url} is about. Use search2 if search is hitting a quota limit. If there is no information about it then continue on to the next step. If it is found to get you in trouble, stop all tasks and finish with a reply to the user \"Not legal to run prompt check on {self.http_url}!!\".",
            # f"Check if {self.http_url} is a valid url to a login form and if not, stop all tasks and finish with a reply to user \"Not a valid form URL. Please provide a actual form URL\"",
            # f"Check if log files {self.info_log_path} and {self.error_log_path} exist and if not, create them",
            f"""
            Run the command below. Don't try to install hydra. If hydra command failed, move on to step 2. Do not use sudo. Be very careful about running this.
            ```bash 
            hydra -v -L {data_path + "/username_list_small.txt"} -P {data_path + "/password_list_small.txt"} {hydra_host} http-post-form "/admin/login/:username=^USER^&password=^PASS^:F=Invalid username or password" > {self.info_log_path} 2> {self.error_log_path}
            ```
            """,
            # f"""
            # If step 1 failed, try this step. If not, continue to step 3. Look into using the selenium python library via REPL. Use the "write_file" command. Using the source of {self.http_url}, write a python program using selenium python and its WebDriver API at {data_path} with name login_test.py. The program has to iterate through the username list {data_path + "/username_list_small.txt"} with every password at {data_path + "/password_list_small.txt"} and try to login at {self.http_url}. Store the python program at {data_path}. Use bash symbols > and 2> to stream to the stdout log {self.info_log_path} and the stderr log {self.error_log_path}. If this doesn't work continue on to next step.
            # """,
            f"""
            If any of the above steps worked, write a summary security report locally at
                {self.summary_file_path}
            using the information log 
                {self.info_log_path} 
            
            Include suggestions, if needed, on what can be done to fix issues.
            
            If the information log is empty just write in report 
                "No security issues found with form at {self.http_url}"

            If the previous steps failed, just write in report
                "FAILURE - No security tools found on machine"
            
            Avoid using any interactive editors

            Finish after report is written
            """,
            # "Congrats, you have completed all the tasks successfully, once the report is created, stop all other tasks"
        ]

        sys.stdout = StreamToLogger(self.logging, logging.INFO)
        self.vectorstore = self._initialise_memory_store()
        self.memory = self.vectorstore.as_retriever()

    def _initialise_memory_store(self):
        """Create the vector store used as long-term memory."""

        if self.config.redis_url:
            try:
                Redis.from_texts(
                    texts=["hacker"],
                    redis_url=self.config.redis_url,
                    index_name=self.uuid,
                    embedding=self.embeddings,
                )

                return Redis(
                    redis_url=self.config.redis_url,
                    index_name=self.uuid,
                    embedding_function=self.embeddings.embed_query,
                )
            except Exception as err:  # pragma: no cover - fallback path
                self.logging.warning(
                    "Redis memory initialisation failed (%s). Falling back to FAISS.",
                    err,
                )

        self.logging.info("Using in-memory FAISS vector store.")
        return FAISS.from_texts(["hacker"], embedding=self.embeddings)
        
    
    def run(self):
        llm = ChatOpenAI(
            temperature=0,
            streaming=True,
            api_key=self.config.openai_api_key,
            model=self.config.openai_model,
        )

        agent = AutoGPT.from_llm_and_tools(
            ai_name=self.uuid,
            ai_role="Penetration Tester",
            tools=self.tools,
            llm=llm,
            memory=self.memory,
        )
        agent.chain.verbose = False

        try:
            self.autogpt_resp = agent.run(self.goals)
        except Exception as err:
            print(f"AutoGPT failure {err}")

        if self.autogpt_resp:
            self.logging.info(f"AutoGPT Response: {self.autogpt_resp}")
