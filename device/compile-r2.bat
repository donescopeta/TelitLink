@echo on
set pythondir="c:\Program Files (x86)\\telitPython"
set file='d:\@w7Users\Ms\\\\telit-workspace\p1\main-r2.py'
set options= -OO -X -S
%pythondir%\python.exe %options% -c "exec(\"print 'compiling:',%file%; import py_compile; py_compile.compile(%file%);\")"
