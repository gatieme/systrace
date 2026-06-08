#ifndef __SYSTRACE_H__
#define __SYSTRACE_H__
#include <unistd.h>
#include <stdio.h>

#if USE_TRACE
extern int __systrace_marker_fd;
extern void __trace_init();

static inline void TRACE_BEGIN(const char *name) {
    __trace_init();
    char buf[1024];
    size_t len = snprintf(buf, 1024, "B|%d|%s", getpid(), name);
    write(__systrace_marker_fd, &buf, len);
}

static inline void TRACE_END() {
    char buf = 'E';
    write(__systrace_marker_fd, &buf, 1);
}
#else

#define TRACE_BEGIN(name) (0)
#define TRACE_END() (0)

#endif

#endif
