import sqlite3
from langgraph.checkpoint.sqlite import SqliteSaver

_conn = sqlite3.connect("agent_memory.db", check_same_thread=False)
checkpointer = SqliteSaver(_conn)
