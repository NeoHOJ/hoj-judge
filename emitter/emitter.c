#include <stdio.h>
#include <unistd.h>
#include <sys/types.h>
#include <signal.h>

const char* PIDFILE = "/tmp/judge.pid";

int main() {
    int pid = -1;
    FILE* f = fopen(PIDFILE, "r");
    if (!f) {
        printf("Fail to obtain judge pid from %s\n", PIDFILE);
        return 1;
    }
    if (fscanf(f, "%d", &pid) != 1 || pid <= 1) {
        printf("Malformed pid file\n");
        return 1;
    }

    fprintf(stderr, "Sending SIGUSR1 to %d...\n", pid);
    int rtn = kill(pid, SIGUSR1);
    if (rtn < 0) {
        perror("Fail to send signal");
        return 1;
    }
}
