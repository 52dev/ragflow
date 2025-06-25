#
#  Copyright 2024 The InfiniFlow Authors. All Rights Reserved.
#
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
#
from abc import ABC
import re
from copy import deepcopy

import pandas as pd
# import pymysql # Removed
# import psycopg2 # Removed
from agent.component import GenerateParam, Generate
# import pyodbc # Removed
import logging


class ExeSQLParam(GenerateParam):
    """
    Define the ExeSQL component parameters.
    """

    def __init__(self):
        super().__init__()
        self.db_type = "mysql"
        self.database = ""
        self.username = ""
        self.host = ""
        self.port = 3306
        self.password = ""
        self.loop = 3
        self.top_n = 30

    def check(self):
        super().check()
        self.check_valid_value(self.db_type, "Choose DB type", ['mysql', 'postgresql', 'mariadb', 'mssql'])
        self.check_empty(self.database, "Database name")
        self.check_empty(self.username, "database username")
        self.check_empty(self.host, "IP Address")
        self.check_positive_integer(self.port, "IP Port")
        self.check_empty(self.password, "Database password")
        self.check_positive_integer(self.top_n, "Number of records")
        if self.database == "rag_flow":
            if self.host == "ragflow-mysql":
                raise ValueError("For the security reason, it dose not support database named rag_flow.")
            if self.password == "infini_rag_flow":
                raise ValueError("For the security reason, it dose not support database named rag_flow.")


class ExeSQL(Generate, ABC):
    component_name = "ExeSQL"

    def _refactor(self, ans):
        ans = re.sub(r"^.*</think>", "", ans, flags=re.DOTALL)
        match = re.search(r"```sql\s*(.*?)\s*```", ans, re.DOTALL)
        if match:
            ans = match.group(1)  # Query content
            return ans
        else:
            print("no markdown")
        ans = re.sub(r'^.*?SELECT ', 'SELECT ', (ans), flags=re.IGNORECASE)
        ans = re.sub(r';.*?SELECT ', '; SELECT ', ans, flags=re.IGNORECASE)
        ans = re.sub(r';[^;]*$', r';', ans)
        if not ans:
            raise Exception("SQL statement not found!")
        return ans

    def _run(self, history, **kwargs):
        input_df = self.get_input()
        sql_query_input = "".join([str(a) for a in input_df["content"]]) if "content" in input_df and not input_df.empty else ""

        logging.info(f"ExeSQL component received input: {sql_query_input[:100]}...")
        logging.info(f"ExeSQL component is running in a no-database environment. SQL execution will be skipped.")

        # Attempt to refactor the input to see if it's a valid SQL, but don't execute
        try:
            refactored_sql = self._refactor(sql_query_input)
            logging.info(f"Refactored SQL (not executed): {refactored_sql}")
        except Exception as e:
            logging.warning(f"Could not refactor SQL from input: {e}")
            # Return a message indicating failure to parse SQL or that the component is disabled
            return ExeSQL.be_output(f"Error processing SQL input or component disabled: {e}")

        # Return a message indicating that the component is non-functional in this environment.
        # Or, return an empty DataFrame as if the query ran and returned no results.
        # For clarity, a message is better.
        message = (f"ExeSQL component is configured for '{self._param.db_type}' "
                   f"but is non-functional as database access is disabled in this environment. "
                   f"Received SQL (not executed): {refactored_sql}")

        # The component is expected to return a DataFrame.
        return ExeSQL.be_output(message)

    def _regenerate_sql(self, failed_sql, error_message, **kwargs):
        logging.info(f"ExeSQL._regenerate_sql called for SQL: {failed_sql}. Error: {error_message}")
        logging.info("SQL regeneration is skipped in no-database environment as the Generate component is mocked.")
        # Since the Generate component (which this class inherits from) is heavily mocked,
        # calling its _run method might not be meaningful or could lead to unexpected behavior
        # depending on the mock's implementation.
        # It's safer to return None or the original failed SQL.
        return None
        # Original logic:
        # prompt = f'''
        ## You are the Repair SQL Statement Helper, please modify the original SQL statement based on the SQL query error report.
        ## The original SQL statement is as follows:{failed_sql}.
        ## The contents of the SQL query error report is as follows:{error_message}.
        ## Answer only the modified SQL statement. Please do not give any explanation, just answer the code.
# '''
        # self._param.prompt = prompt
        # kwargs_ = deepcopy(kwargs)
        # kwargs_["stream"] = False
        # response = Generate._run(self, [], **kwargs_) # Generate._run will use mocked LLM
        # try:
        #     regenerated_sql = response.loc[0, "content"]
        #     return regenerated_sql
        # except Exception as e:
        #     logging.error(f"Failed to regenerate SQL (using mock Generate): {e}")
        #     return None

    def debug(self, **kwargs):
        logging.info("ExeSQL.debug called. Running _run in no-database mode.")
        return self._run([], **kwargs)
