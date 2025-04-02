@REM This batch file is used to run the photo_id module with specific arguments.
@REM It activates the Python virtual environment and executes the photo_id script.

@REM The command below runs the photo_id module with the following options:
@REM --verbose: Enables verbose output for detailed logging.
@REM --have_list: Specifies the path to the CSV file containing the list of species.

@REM Usage:
@REM To use this batch file, simply double-click it or run it from the command line.
@REM Ensure that the virtual environment is set up and the required dependencies are installed.

@REM Example:
@REM Double-click the photo_id.bat file or run the following command in the command line:
@REM C:\Users\Guy\GitProjects\photo-id\photo_id.bat
C:\Users\Guy\GitProjects\photo-id\.venv\Scripts\python.exe -m photo_id.photo_id --verbose --have_list  C:\Users\Guy\GitProjects\photo-id\tests\data\guy_ebird_world_life_list_1224.csv