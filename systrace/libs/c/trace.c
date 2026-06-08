#include <fcntl.h>
#include <sys/stat.h>
#include <pthread.h>
#include "trace.h"

#define TRACE_MARKER "/sys/kernel/debug/tracing/trace_marker"

static pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
int __systrace_marker_fd = -1;

void __trace_init() {
    pthread_mutex_lock(&mutex);
    static int systrace_initialized = 0;
    if (systrace_initialized) {
        pthread_mutex_unlock(&mutex);
        return;
    }

    __systrace_marker_fd = open(TRACE_MARKER, O_WRONLY);
    systrace_initialized = 1;
    pthread_mutex_unlock(&mutex);
}
