AttributeError: This app has encountered an error. The original error message is redacted to prevent data leaks. Full error details have been recorded in the logs (if you're on Streamlit Cloud, click on 'Manage app' in the lower right of your app).
Traceback:
File "/mount/src/stock-3d-app/streamlit_app.py", line 646, in <module>
    x=df_chart['DateTime'].dt.strftime(time_fmt),
      ^^^^^^^^^^^^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/generic.py", line 6194, in __getattr__
    return object.__getattribute__(self, name)
           ~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/accessor.py", line 230, in __get__
    return self._accessor(obj)
           ~~~~~~~~~~~~~~^^^^^
File "/home/adminuser/venv/lib/python3.14/site-packages/pandas/core/indexes/accessors.py", line 698, in __new__
    raise AttributeError("Can only use .dt accessor with datetimelike values")
