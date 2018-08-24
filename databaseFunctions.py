# -*- coding: utf-8 -*-

# WHAT THIS CODE DOES
# 1) Imports necessary modules (for both functions)
# 2) Sets database variables inc username and password (for both functions)

# 3) Function to extract table from a database into a pandas dataframe

# 4) Function to copy table between databases


# //////////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////////
# 
# 1) Necessary imports
import math
import time
import pandas as pd
import sqlalchemy
from sqlalchemy import create_engine


# //////////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////////
# 
# 2) Database variables
pg_username = '...'
pg_host = '...'
pg_port = '...'
pg_database = '...'

rs_username = '...'
rs_host = '...'
rs_port = '...'
rs_database = '...'

# Extract your database passwords - ideally using keyring from Windows Credentials
import keyring
pg_password = keyring.get_password(pg_database, pg_username)
rs_password = keyring.get_password('redshift', rs_username)

# //////////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////////
# 
# 3) Function to extract table from a database into a pandas dataframe

def getTableFromDatabase( username,
                          password,
                          host,
                          port,
                          database,
                          stmt):

  # Set up connection to database
  try:
    connection = create_engine('postgresql://{username}:{password}@{host}:{port}/{database}'.format(username = username,
                                                                                                    password = password,
                                                                                                    host = host,
                                                                                                    port = port,
                                                                                                    database = database))
    print("Connexion to {} successful".format(database))
  except:
    print('#######################################################')
    print ("Unable to open database {}".format(database))
    print ('#######################################################')
    return False

  # Extract table from database
  print('Running query')
  dataframe = pd.read_sql(stmt, connection)
  print(len(dataframe.index), "records fetched successfully")
  return dataframe

# //////////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////////
# 
# 4) Function to copy table between databases


# Only include base_table_stmt if you want to explicitly set the datatypes of the to_columns
# MUST include first column as rn (row number), and columns MUST be in the correct order
# -----------
# base_table_stmt = """
#       CREATE TABLE to_schema.to_tablename
#       (
#       rn DOUBLE PRECISION,  # (rownumber column must stay) 
#       acorn_code INTEGER,   # (just an example)
#       ...
#       )
#       """

def copyTableBetweenDatabases(from_username,
                              from_password,
                              from_host,
                              from_port,
                              from_database,
                              from_schema,
                              from_tablename,
                              to_username,
                              to_password,
                              to_host,
                              to_port,
                              to_database,
                              to_schema,
                              to_tablename,
                              rows_in_segment = 10**4,
                              base_table_stmt = None):
  
  start_time = time.time()

  # Set up connection to from_database
  try:
    con_from = create_engine('postgresql://{username}:{password}@{host}:{port}/{database}'.format(username = from_username,
                                                                                                password = from_password,
                                                                                                host = from_host,
                                                                                                port = from_port,
                                                                                                database = from_database))
    print("Connexion to {} successful".format(from_database))
  except:
    print('#######################################################')
    print ("Unable to open database {}".format(from_database))
    print ('#######################################################')
    return False
  
  # Set up connection to to_database
  try:
    con_to = create_engine('postgresql://{username}:{password}@{host}:{port}/{database}'.format(username = to_username,
                                                                                              password = to_password,
                                                                                              host = to_host,
                                                                                              port = to_port,
                                                                                              database = to_database))
    print("Connexion to {} successful".format(to_database))
  except:
    print('#######################################################')
    print ("Unable to open database {}".format(to_database))
    print ('#######################################################')
    return False
  
  # Explicitly set the datatypes of the to_columns by pre-creating the table - default is None
  if base_table_stmt is not None:
    con_to.execute(base_table_stmt)
  
  # Get number of segments = rows divided by rows_in_segment (default is 10**5)
  sSQL = "SELECT COUNT(*) FROM {}.{}".format(from_schema, from_tablename)
  df_length = pd.read_sql(sSQL, con_from)
  num_segments = math.ceil(df_length.iloc[0]['count']/rows_in_segment)

  # Set initial variables for loop
  start_row = 1
  end_row = rows_in_segment

  # Loop over segments (separate table into segments in order not to max out memory)
  for i in range(num_segments):
    print('Proccessing row {} to row {}. \n  On query {} of {}'.format(start_row, end_row, i+1, num_segments))
    # Selects only relevant part of table from from_database
    load_data_sql = "WITH cte as (SELECT row_number () OVER (ORDER BY 1) AS rn, * FROM {}.{}) \
                          SELECT * FROM cte WHERE rn BETWEEN {} AND {}".format(from_schema, from_tablename, start_row, end_row) 
    df_pg = pd.read_sql(load_data_sql, con_from)
    # Loads selected data into the to_database
    print("sending data to to_database")
    df_pg.to_sql(name=to_tablename, con=con_to, index=False, schema=to_schema, if_exists="append", chunksize=1000)
    # Increment loop variables 
    start_row += rows_in_segment
    end_row += rows_in_segment
    print('Finished processing query {} of {}'.format(i+1, num_segments))

  # Prints summary stats from process
  print("table {}.{} created in {}".format(to_schema, to_tablename, to_database))
  print("---- {} seconds ----".format(time.time() - start_time))
  print("---- {} minutes ----".format((time.time() - start_time)/60))
  return True

# //////////////////////////////////////////////////////////////////////////////////////////////////////////
# //////////////////////////////////////////////////////////////////////////////////////////////////////////

