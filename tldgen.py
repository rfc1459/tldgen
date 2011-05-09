#!/usr/bin/env python

# Azzurra IRC Services TLD DFA generator
# Copyright (C) 2011 Matteo Panella <morpheus@azzurra.org> 
#
# This program is free but copyrighted software; please check COPYING
# for more details.

from __future__ import with_statement

# Acceptance states (and flags)
ACCEPT_MAIL = 1
ACCEPT_HOST = 2
ACCEPT_ALL  = ACCEPT_MAIL | ACCEPT_HOST

# pseudo-TLDs used internally by some Azzurra ircds
PSEUDO_TLDS = (
    ('fw',  ACCEPT_HOST),
    ('lan', ACCEPT_ALL ),
    ('thc', ACCEPT_HOST),
)

# Template for the header file itself
C_HDR_TMPL = """/*
 * Azzurra IRC Services (C) 2001-2011 Azzurra IRC Network
 *
 * This program is free but copyrighted software; see COPYING for details.
 *
 * tld_tab.h - DFA state matrix for TLD check
 * THIS FILE IS AUTOGENERATED - DO NOT EDIT!
 */

#ifndef I_HAVE_A_VERY_GOOD_REASON_TO_INCLUDE_TLD_TAB_H
#error "*NEVER* *EVER* include this file unless you know what you're doing"
#endif /* I_HAVE_A_VERY_GOOD_REASON_TO_INCLUDE_TLD_TAB_H */

#define ACCEPT_MAIL %(accept_mail_val)d
#define ACCEPT_HOST %(accept_host_val)d

/* Token values */
enum
{
    TLD_TOK_INVALID = -1,
%(token_enum)s
};

#define TRANS_TBL_SIZE %(trans_tbl_size)d

/* DFA state */
typedef struct _dfa_state
{
    /* State number is implicitly defined by order in state array.
     * Also, initial state is always state 0.
     */
     unsigned char flags;                   /* TLD flags (0 if state is not final) */
     short transitions[TRANS_TBL_SIZE];     /* Transition table (indexed by token) */
} dfa_state;

/* Mapping function from character to token */
static inline int token_value(unsigned char t)
{
    switch (t)
    {
%(token_map_statements)s
    default:
        return TLD_TOK_INVALID;
    }
}

/* The state array itself (YIKES!) */
static dfa_state tld_dfa[] = {
%(dfa_state_entries)s
};"""

# Template for token enum entries
C_ENUM_TMPL = "    %(enum_name)s = %(enum_value)d"

# Template for token mapping statements
C_MAP_STATEMENT_TMPL = """    case '%(token)c':
        return %(enum_name)s;"""

# Template for state table entries
C_DFA_ENTRY_TMPL = "    {%(flags)d, %(trans_tbl)s}"

class State(object):
    """A DFA state"""
    def __init__(self, statenum, is_start=False, is_final=False, fval=None):
        self.statenum = statenum
        self.is_start = is_start
        self.is_final = is_final
        self.fval = fval
        self.transitions = {}

    def add_transition(self, symbol, state):
        next_states = self.transitions.get(symbol, [])
        next_states.append(state)
        self.transitions[symbol] = next_states

    def __str__(self):
        s = []
        s.append('State: %d' % self.statenum)
        if self.is_start:
            s.append(' start state\n')
        elif self.is_final:
            s.append(' final state (value: %r)\n' % self.fval)
        else:
            s.append('\n')
        for (sym, next_states) in self.transitions.items():
            for next_state in next_states:
                s.append('  %s -> %d\n' % (sym, next_state.statenum))
        return ''.join(s)

class DFA(object):
    """A Deterministic Finite Automaton"""
    def __init__(self):
        self.start_state = None
        self.states = set()
        self.statenum_map = {}

    def add_state(self, statenum, start=False, final=False, value=None):
        """Add a new state to the DFA and return it"""
        new_state = State(statenum, start, final, value)
        self.states.add(new_state)
        self.statenum_map[statenum] = new_state

        if start == True:
            self.start_state = new_state

        return new_state

    def add_transition(self, curr_statenum, next_statenum, symbol):
        """Add a transition"""
        try:
            curr_state = self.statenum_map[curr_statenum]
        except KeyError:
            curr_state = self.add_state(curr_statenum)

        try:
            next_state = self.statenum_map[next_statenum]
        except KeyError:
            next_state = self.add_state(next_statenum)

        trans = curr_state.transitions.get(symbol, [])
        if next_state not in trans:
            trans.append(next_state)
        curr_state.transitions[symbol] = trans

    def get_next_state(self, curr_state, symbol):
        """Get transition for a symbol"""
        if symbol in curr_state.transitions:
            next_states = curr_state.transitions[symbol]
            next_state = next_states[0]
            return next_state
        else:
            return None

    def test_string(self, s):
        """Test if given string is accepted by this DFA"""
        curr = self.start_state
        for sym in s:
            curr = self.get_next_state(curr, sym)
            if curr is None:
                return False

        return curr.is_final

    def print_states(self, fd):
        print >>fd, '\nStates of DFA:\n'
        for statenum in sorted(self.statenum_map.keys()):
            print >>fd, self.statenum_map[statenum]

class Trie(DFA):
    """A trie (backed by a DFA)"""
    def __init__(self):
        DFA.__init__(self)
        self.statenum = 0

    def add_string(self, s, val=None):
        """Add a new string to the Trie"""
        # Create start state if necessary
        if self.start_state is None:
            self.add_state(self.statenum, start=True)
            self.statenum += 1

        # Find the last state for a prefix of the string
        curr = self.start_state
        i = 0
        while i < len(s):
            next_state = self.get_next_state(curr, s[i])
            if next_state is None:
                break
            else:
                i += 1
                curr = next_state

        # Create new states for remaining characters
        for j in xrange(i, len(s)):
            sym = s[j]
            new_state = self.add_state(self.statenum)
            self.statenum += 1
            self.add_transition(curr.statenum, new_state.statenum, sym)
            curr = new_state

        # State for last symbol is final
        curr.is_final = True
        curr.fval = val

    def get_language(self):
        """Return a list of strings accepted by this trie"""
        lang = []
        def get_lang(so_far, curr, lang):
            if curr.is_final:
                lang.append(''.join(so_far))
            for (sym, next_states) in curr.transitions.items():
                next_state = next_states[0]
                so_far.append(sym)
                get_lang(so_far, next_state, lang)
                so_far.pop()
        get_lang([], self.start_state, lang)
        return lang

def load_tld_list(name='tlds-alpha-by-domain.txt'):
    """Parse IANA TLD file"""
    tlds = []
    with open(name, 'r') as f:
        for l in f:
            # Skip empty lines and comments
            l = l.strip()
            if len(l) == 0 or l[0] == '#':
                continue
            # Filter out IDNs
            if l.startswith('XN--'):
                continue
            tlds.append((l.lower(), ACCEPT_ALL))

    # Append local TLDs
    tlds.extend(PSEUDO_TLDS)
    # Sort the resulting list
    tlds.sort(lambda x, y: cmp(x[0], y[0]))
    # And return it
    return tlds

def generate_dfa(tlds):
    """Generate a DFA from given TLD list"""
    dfa = Trie()
    for tld in tlds:
        dfa.add_string(tld[0], tld[1])
    return dfa

def generate_token_map(lang):
    """Generate a token map for given language"""
    tmap = {}
    tidx = 0
    for s in lang:
        for c in s:
            if c not in tmap:
                tmap[c] = (c, tidx, 'TLD_TOK_%02d' % tidx)
                tidx += 1
    return sorted(tmap.values(), lambda x, y: cmp(x[1], y[1]))

def generate_state(token_map, state):
    # Encode state flags
    template_data = {}
    template_data['flags'] = state.fval if state.is_final and state.fval is not None else 0
    # Encode transitions list - start with all transitions being non-valid
    trans_list = [-1] * len(token_map)
    for (sym, next_states) in state.transitions.items():
        tridx = token_map[sym][0]
        assert len(next_states) == 1, "Internal DFA error: more than one transition for a symbol (BUG!)"
        trans_list[tridx] = next_states[0].statenum
    template_data['trans_tbl'] = '{%s}' % (','.join(['%d' % t for t in trans_list]))
    return C_DFA_ENTRY_TMPL % template_data

def build_c_header(dfa):
    """Build the header file from a given DFA instance"""
    template_data = {
        'accept_mail_val'       : ACCEPT_MAIL,
        'accept_host_val'       : ACCEPT_HOST,
    }
    tmap = generate_token_map(dfa.get_language())
    # Create enum string
    template_data['token_enum'] = ',\n'.join([C_ENUM_TMPL % {'enum_name': token[2], 'enum_value': token[1]} for token in tmap])
    # Define transition table size
    template_data['trans_tbl_size'] = len(tmap)
    # Assemble token mapping statements
    template_data['token_map_statements'] = '\n'.join([C_MAP_STATEMENT_TMPL % {'token': token[0], 'enum_name': token[2]} for token in tmap])
    # Now a tough one: generate the DFA state table
    states = [stm[1] for stm in sorted(dfa.statenum_map.items(), lambda x, y: cmp(x[0], y[0]))]
    # Ensure first state has statenum 0 and starting state flag set
    assert states[0].statenum == 0 and states[0].is_start, "Consistency error: first state is not the DFA root state (BUG!)"
    # Re-arrange token map
    token_map = dict([(t[0], t[1:]) for t in tmap])
    # Serialize all states
    template_data['dfa_state_entries'] = ',\n'.join([generate_state(token_map, state) for state in states])
    # Build template
    return C_HDR_TMPL % template_data

if __name__ == '__main__':
    tlds = load_tld_list()
    dfa = generate_dfa(tlds)
    c_header = build_c_header(dfa)

    # Write C header to file
    with open('tld_tab.h', 'w') as chdr_out:
        chdr_out.write(c_header)
        chdr_out.write('\n')
        chdr_out.flush()

    # Generate statistics
    with open('tld_stats.txt', 'w') as stats_out:
        print >>stats_out, "Language accepted by this DFA:"
        for l in sorted(dfa.get_language()):
            print >>stats_out, "    %s" % l
        dfa.print_states(stats_out)
        stats_out.flush()
