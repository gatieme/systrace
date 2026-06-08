@echo ####clearing hitrace to (%date% %time%) ...
hdc shell "rm -rvf /data/log/hitrace/*"

@echo ####starting hitrace to (%date% %time%) ...
hdc shell hitrace --trace_begin --record ace ark app ohos ability graphic sched freq nweb workq pagecache binder irq disk memreclaim samgr sync zcamera zmedia commonlibrary net zaudio idle ufs rpc distributeddatamgr dsoftbus i2c mdfs misc mmc msdp multimodalinput notification regulators  sensors window zimage ffrt --file_size 204800 -b 147456
@pause

@echo ####stoping hitrace to (%date% %time%) ...
hdc shell hitrace --trace_finish --record
@pause

@for /f "tokens=* delims= " %%i in ('powershell.exe -Command "Get-Date -Format 'yyyyMMdd_HHmmss'"') do @set "datetime=%%i"
set folder=".\traces\hitrace_%datetime%"
@echo ####start get hitrace to (%CD%\%folder%) ...
hdc file recv /data/log/hitrace  %folder%

@echo ============ done! =============
@pause