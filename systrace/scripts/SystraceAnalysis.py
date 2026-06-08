import time
import re
import sys
import getopt
import os
import sys
 
reload(sys)
sys.setdefaultencoding('utf-8')

#Get the timestamp of a row
class SystraceCalcTime:
    time = 0
    def __init__(self, str):
        timeIsSet= False
        str = str.strip('\r\n')
        for s in str.split(' '):
            if(timeIsSet is not True):
                m = re.match(r'(\d+\.\d\d\d\d\d\d)(\:)',s)
                if(m):
                    self.time = float(s[m.start(1):m.end(1)])
                    timeIsSet = True
                    continue

#In a line, get the timestamp containing the particular string
def ObtainStartTime(string, line):
    stri = re.search(string, line)
    if(stri is not None):
        return SystraceCalcTime(line).time

def SystraceAnalysis(inputFileName, outputFileName, add_delta):
    fInput = open(inputFileName, 'rb')
    fOutput = open(outputFileName, 'a')

    line_num = 0
    trace_start_time = 0
    trace_time = 0
    delta_time = ''

    irq_time = 0
    irq_time_count = 0
    ipi_time = 0
    ipi_time_count = 0
    sched_switch = 0
    sched_switch_count = 0
    sched_wakeup_count = 0

#Traversing line by line for input files
    for line in fInput:
        line = line.decode('utf-8')
        line_num += 1

#Filtering useless data
        if(line_num < 6126):
#            fOutput.write(line)
            continue

#Look for specific characters and first successful search. 
#Compare the three timestamps, which is the smallest and which is the zero point
        if(irq_time_count == 0):
            irq_time = ObtainStartTime("irq_handler_entry", line)
            if(irq_time is not None):
                irq_time_count = 1
        
        if(ipi_time_count == 0):
            ipi_time = ObtainStartTime("ipi_raise", line)
            if(ipi_time is not None):
                ipi_time_count = 1

        string = re.search("sched_wakeup", line)
        if(string is not None and sched_wakeup_count == 0 and sched_switch_count == 0):
            sched_wakeup_count = 1

        if(sched_wakeup_count == 1 and sched_switch_count == 0):
            sched_switch = ObtainStartTime("sched_switch", line);
            if(sched_switch is not None):
                sched_wakeup_count = 0
                sched_switch_count = 1

#contine search zero point
        if(irq_time_count == 0 and ipi_time_count == 0 and sched_switch_count == 0):
            fOutput.write(line)
            continue

#Convenient calculation
        if(irq_time_count == 0):
            irq_time = 100000000;

        if(ipi_time_count == 0):
            ipi_time = 100000000

        if(sched_switch_count == 0):
            sched_switch = 100000000

#obtain mim value
        if(irq_time > ipi_time):
            trace_start_time = ipi_time
            if(trace_start_time > sched_switch):
                trace_start_time = sched_switch
        else:
            trace_start_time = irq_time
            if(trace_start_time > sched_switch):
                trace_start_time = sched_switch

#Calculate the difference from the zero point
        trace_time = SystraceCalcTime(line).time
        delta_time = str(round(trace_time - trace_start_time + float(add_delta)/1000000, 6))
        delta_time = delta_time + ":"

#delta_time replace original value and the new line will be written to the output file.
        line = re.sub('(\d+\.\d\d\d\d\d\d)(\:)',delta_time,line)
        fOutput.write(line)

    fOutput.close()
    fInput.close()

def Usage():
    print('Idle Analyzer Usage:')
    print('-h, --help: print help message. (Optional)')
    print('-v, --version: print version. (Optional)')
    print('-i, --input: input file. (Optional, default value: trace)')
    print('-o, --output: output file. (Optional, default value: hour-miunte-second.log)')
    print('-l, --list: show current while list. (Optional)')
    print('-d, --add: add delta vaule for systrace zero point')
    print('e.x. IdleAnalyzer.py -i trace -o output.log -t 0.001')

def Version():
    print('Systrace Analyzer v0.2')

def Main(argv):
    inputFile = 'trace'
    outputFile = time.strftime('%H-%M-%S',time.localtime(time.time())) + '.log'
    add_delta = 0.001
    try:
        opts, args = getopt.getopt(argv[1:], 'hvi:o:d:', ['input=', 'output='])
    except getopt.GetoptError as err:
        print(str(err))
        Usage()
        sys.exit(1)
    for o, a in opts:
        if o in ('-h', '--help'):
            Usage()
            sys.exit(0)
        elif o in ('-v', '--version'):
            Version()
            sys.exit(0)
        elif o in ('-i', '--input'):
            inputFile = a
        elif o in ('-o', '--output'):
            outputFile = a
        elif o in ('-d', '--add'):
            add_delta = float(a)
        else:
            print('unhandled option')
            sys.exit(1)
    if(os.path.exists(outputFile)): os.remove(outputFile)

    SystraceAnalysis(inputFile, outputFile, add_delta)

if __name__ == '__main__':
    Main(sys.argv)
