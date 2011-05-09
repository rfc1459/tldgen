# fsm.py - Finite State Machine classes
# Azzurra IRC Services TLD DFA generator
# Copyright (C) 2011 Matteo Panella <morpheus@azzurra.org> 
#
# This program is free but copyrighted software; please check COPYING
# for more details.

__all__ = ['DFA', 'Trie', 'State']

class AlreadyFinalizedError(Exception):
    pass

class Token(object):
    def __init__(self, sym, index, prefix='TLD_TOK_'):
        self.sym = sym
        self.index = index
        self.prefix = 'TLD_TOK_'

    def __str__(self):
        return '%s%d' % (self.prefix, self.index)

    def __repr__(self):
        return '<Token(%r, %r, %r)>' % (self.sym, self.index, self.prefix)

class State(object):
    """A DFA state"""
    def __init__(self, statenum, is_start=False, is_final=False):
        self.statenum = statenum
        self.is_start = is_start
        self.is_final = is_final
        self.transitions = {}

    def add_transition(self, symbol, state):
        # A DFA may only have one transition per symbol (silly me...)
        assert self.transitions.get(symbol) is None, "Internal error: multiple transitions for single symbol"
        self.transitions[symbol] = state

    def __str__(self):
        s = []
        s.append('State: %d' % self.statenum)
        if self.is_start:
            s.append(' start state\n')
        elif self.is_final:
            s.append(' final state\n')
        else:
            s.append('\n')
        for (sym, next_state) in self.transitions.items():
            s.append('  %s -> %d\n' % (sym, next_state.statenum))
        return ''.join(s)

    def __repr__(self):
        return '<State(%r, is_start=%r, is_final=%r)>' % (self.statenum, self.is_start, self.is_final)

class DFA(object):
    """A Deterministic Finite Automaton"""
    def __init__(self):
        self.start_state = None
        self.states = set()
        self.statenum_map = {}

    def add_state(self, statenum, start=False, final=False):
        """Add a new state to the DFA and return it"""
        new_state = State(statenum, start, final)
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

        curr_state.add_transition(symbol, next_state)

    def get_next_state(self, curr_state, symbol):
        """Get transition for a symbol"""
        if symbol in curr_state.transitions:
            return curr_state.transitions[symbol]
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
            for next_state in current.transitions.values():
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
        self.__finalized = False

    def add_string(self, s):
        """Add a new string to the Trie"""
        if self.__finalized:
            raise AlreadyFinalizedError()
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

    def __finalize_visit_fn(self, current, visited, dangling):
        """Visit function for state optimization"""
        if current not in visited:
            visited.add(current)
            for (sym, state) in current.transitions.items():
                if state in visited:
                    continue
                elif state.is_final and len(state.transitions) == 0:
                    dangling.add(state)
                    visited.add(state)
                    current.transitions[sym] = self.__final_state
                else:
                    self.__finalize_visit_fn(state, visited, dangling)

    def __renumber_visit_fn(self, current, visited):
        if current not in visited:
            current.statenum = self.statenum
            self.statenum_map[self.statenum] = current
            self.statenum += 1
            visited.add(current)
        for next_state in current.transitions.values():
            if next_state not in visited:
                self.__renumber_visit_fn(next_state, visited)

    def finalize(self):
        """Coalesce all final states without into a single one and renumber all states"""
        if self.__finalized:
            return
        assert self.is_valid(), "Internal error: Trie.finalized cannot be called on an invalid DFA"
        # Synthesize final state
        self.__final_state = self.add_state(self.statenum, final=True)
        # Recursively visit all states, replace final states without outgoing transitions with
        # synthetic final state and collect them in a set
        dangling = set()
        self.__finalize_visit_fn(self.start_state, set([self.__final_state]), dangling)
        # Remove dangling states from state set
        self.states.difference_update(dangling)
        # Reverify validity
        assert self.is_valid(), "Internal error: optimized Trie has unreachable states"
        # Renumber all states
        self.statenum = 0
        self.statenum_map = {}
        self.__renumber_visit_fn(self.start_state, set())
        self.__finalized = True

    def get_language(self):
        """Return a list of strings accepted by this trie"""
        lang = []
        def get_lang(so_far, curr, lang):
            if curr.is_final:
                lang.append(''.join(so_far))
            for (sym, next_state) in curr.transitions.items():
                so_far.append(sym)
                get_lang(so_far, next_state, lang)
                so_far.pop()
        get_lang([], self.start_state, lang)
        return lang

    def _get_tokenmap_internal(self):
        """For internal use only."""
        lang = self.get_language()
        tmap = {}
        tidx = 0
        for s in lang:
            for sym in s:
                if sym not in tmap:
                    tmap[sym] = Token(sym, tidx)
                    tidx += 1
        return tmap

    def get_tokens(self):
        """Return a token map for the language accepted by this trie"""
        return sorted(self._get_tokenmap_internal().values(), key=lambda token: token.index)

    def get_state_matrix(self):
        """Get the state matrix for this trie"""
        states = sorted(self.statenum_map.values(), key=lambda state: state.statenum)
        assert states[0].statenum == 0 and states[0].is_start, "Consistency error: first state is not the DFA root state (BUG!)"
        stm = []
        token_map = self._get_tokenmap_internal()
        for state in states:
            tlist = [-1] * len(token_map)
            for (sym, next_state) in state.transitions.items():
                tridx = token_map[sym].index
                tlist[tridx] = next_state.statenum
            stm.append((state.is_final, tuple(tlist)))
        return stm
