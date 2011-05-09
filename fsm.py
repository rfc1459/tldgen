# fsm.py - Finite State Machine classes
# Azzurra IRC Services TLD DFA generator
# Copyright (C) 2011 Matteo Panella <morpheus@azzurra.org> 
#
# This program is free but copyrighted software; please check COPYING
# for more details.

__all__ = ['DFA', 'Trie', 'State']

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

    def is_valid(self):
        """Validate this DFA.
        Requirements:
         * start state MUST be unique;
         * one or more final states;
         * all states MUST be reachable from start state.
        """
        if self.start_state is None:
            return False

        final_found = any([state.is_final for state in self.states])
        if not final_found:
            return False

        def visit_state(current, visited):
            if current not in visited:
                visited.add(current)
            for next_states in current.transitions.values():
                for next_state in next_states:
                    if next_state not in visited:
                        visit_state(next_state, visited)

        visited = set()
        visit_state(self.start_state, visited)

        return len(visited) == len(self.states)

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
