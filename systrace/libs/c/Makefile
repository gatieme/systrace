target: all
all: libtrace.a trace_test

CFLAGS := -Os -fPIC -Wall -pthread

libtrace.a: trace.o
	$(AR) r $@ $^

trace_test: test.c libtrace.a
	$(CC) -Wall -o $@ -ltrace -L. -I. -DUSE_TRACE $^

trace.o: trace.c
	$(CC) $(CFLAGS) -c -o $@ $^ -I .

clean:
	rm -f trace_test libtrace.a trace.o
