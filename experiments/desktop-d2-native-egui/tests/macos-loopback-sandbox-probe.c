#include <arpa/inet.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <unistd.h>

/* Synthetic loopback-only App Sandbox network probe; not product networking. */
int main(int argc, char **argv) {
    if (argc != 2) {
        fputs("expected local loopback port\n", stderr);
        return 3;
    }
    char *end = NULL;
    long number = strtol(argv[1], &end, 10);
    if (end == argv[1] || *end != '\0' || number < 1 || number > 65535) {
        fputs("invalid loopback port\n", stderr);
        return 3;
    }
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    if (fd < 0) {
        perror("socket");
        return 3;
    }
    struct sockaddr_in addr = {0};
    addr.sin_family = AF_INET;
    addr.sin_port = htons((unsigned short)number);
    if (inet_pton(AF_INET, "127.0.0.1", &addr.sin_addr) != 1) {
        close(fd);
        return 3;
    }
    int rc = connect(fd, (const struct sockaddr *)&addr, sizeof(addr));
    if (rc == 0) {
        puts("LOOPBACK_CONTROL_CONNECT_ALLOWED");
        close(fd);
        return 0;
    }
    int saved_errno = errno;
    fprintf(stderr, "LOOPBACK_CONNECT_REJECTED errno=%d (%s)\n",
            saved_errno, strerror(saved_errno));
    close(fd);
    return saved_errno == EPERM || saved_errno == EACCES ? 77 : 1;
}
