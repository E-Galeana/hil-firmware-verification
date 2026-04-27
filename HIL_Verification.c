#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <stdbool.h>

#include "pico/stdlib.h"

typedef enum {
    STATE_STANDBY = 0,
    STATE_ACTIVE = 1,
    STATE_FAILSAFE = 2
} system_state_t;

static const char* state_to_str(system_state_t s) {
    switch (s) {
        case STATE_STANDBY: return "STANDBY";
        case STATE_ACTIVE: return "ACTIVE";
        case STATE_FAILSAFE: return "FAILSAFE";
        default: return "UNKNOWN";
    }
}

static system_state_t g_state = STATE_STANDBY;

static void handle_line(const char *line) {
    // REQ-005: Handle empty commands
    if (strlen(line) == 0) {
        printf("ERR UNKNOWN_CMD\n");
        return;
    }

    if (strcmp(line, "PING") == 0) {
        printf("OK PONG\n");
        return;
    }

    if (strcmp(line, "VERSION") == 0) {
        printf("OK VERSION 0.1\n");
        return;
    }

    if (strcmp(line, "GET_STATE") == 0) {
        printf("OK STATE %s\n", state_to_str(g_state));
        return;
    }

    int new_state = -1;
    char extra;
    // REQ-012: Use extra char check to reject floats like "SET_STATE 1.5"
    int parsed = sscanf(line, "SET_STATE %d%c", &new_state, &extra);
    if (parsed == 1) {
        // REQ-003: Boundary check
        if (new_state < 0 || new_state > 2) {
            printf("ERR BAD_STATE\n");
            return;
        }

        // REQ-007: Illegal transition check
        if (g_state == STATE_FAILSAFE && new_state == STATE_ACTIVE) {
            printf("ERR ILLEGAL_TRANSITION\n");
            return;
        }

        g_state = (system_state_t)new_state;
        printf("OK STATE %s\n", state_to_str(g_state));
        return;
    }

    // REQ-005: Unrecognized command
    printf("ERR UNKNOWN_CMD\n");
}

int main(void) {
    stdio_init_all();

    sleep_ms(1500);
    printf("BOOT OK\n");

    char buf[128];
    size_t idx = 0;
    bool overflow_mode = false; // REQ-006: Safe-drop flag

    while (true) {
        int ch = getchar_timeout_us(0);
        if (ch == PICO_ERROR_TIMEOUT) {
            tight_loop_contents();
            continue;
        }

        if (ch == '\r') {
            continue;
        }

        if (ch == '\n') {
            // REQ-006: If in overflow mode, silently discard the line
            if (overflow_mode) {
                overflow_mode = false;
            } else {
                buf[idx] = '\0';
                handle_line(buf); // Removed idx > 0 guard, handle_line handles empty strings
            }
            idx = 0;
            continue;
        }

        // REQ-006: Actively drop characters while in overflow mode
        if (overflow_mode) {
            continue;
        }

        if (idx < sizeof(buf) - 1) {
            buf[idx++] = (char)ch;
        } else {
            // REQ-006: Trigger error
            printf("ERR LINE_TOO_LONG\n");
            overflow_mode = true;
            idx = 0;
        }
    }
}
