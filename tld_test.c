/*
 * Azzurra IRC Services (C) 2001-2011 Azzurra IRC Network
 *
 * This program is free but copyrighted software; see COPYING for details.
 *
 * tld_torture_test.c - Tests for tld_tab.h
 */

#include <stdio.h>
#include <stdlib.h>
#include <stdbool.h>
#define I_HAVE_A_VERY_GOOD_REASON_TO_INCLUDE_TLD_TAB_H
#include "tld_tab.h"

static bool check_tld(const unsigned char *tld, bool forMail)
{
    int token;
    int statenum = 0;
    while (*tld)
    {
        token = token_value(*tld);
        if (token == TLD_TOK_INVALID)
            return false;
        /* Get next state */
        statenum = tld_dfa[statenum].transitions[token];
        if (statenum == -1)
            return false;
        tld++;
    }
    return forMail ? (tld_dfa[statenum].flags & ACCEPT_MAIL) == ACCEPT_MAIL : (tld_dfa[statenum].flags & ACCEPT_HOST) == ACCEPT_HOST;
}

const char *testdoms[] = {
    "it",
    "com",
    "org",
    "eu",
    "arpa",
    "fw",
    "lan",
    "trap",
    "thc",
    "museum",
    "jobs",
    NULL
};

int main(int argc, char **argv)
{
    const char *dom = *testdoms;
    const char **tdptr = testdoms;
    while (dom)
    {
        printf("%s (mail): %d\n", dom, check_tld(dom, true));
        printf("%s (nomail): %d\n", dom, check_tld(dom, false));
        dom = *(tdptr++);
    }
    exit(EXIT_SUCCESS);
}
