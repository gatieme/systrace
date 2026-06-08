#include "trace.h"

int main() {
    TRACE_BEGIN("sleep");
    sleep(1);
    TRACE_END();
    return 0;
}
