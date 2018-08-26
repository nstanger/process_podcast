#!/usr/bin/env python3

import sys
import time


class ProgressBar(object):
    """A simple progress bar with a percent completed value."""
    
    def __init__(self, initial_value=0, max_value=100, print_width=50,
                 newline="\r", quiet=False):
        self.value = self.initial_value = initial_value
        self.max_value = max_value
        self.print_width = print_width
        self.newline = newline
        self.quiet = quiet
    
    def set(self, value=0):
        """Set the current value of the progress bar."""
        self.value = value
    
    def reset(self):
        """Reset the progress bar to its initial value."""
        self.set(value=self.initial_value)
        
    def finish(self):
        """Complete the progress bar by setting it to its maximum value."""
        self.update(value=self.max_value)
        if not self.quiet:
            print()
    
    def update(self, value=0):
        """Set the current value of the progress bar and redraw it."""
        self.set(value)
        self.draw()
    
    def draw(self):
        """Draw the current state of the progress bar."""
        if not self.quiet:
            percent = int(self.value * 100 / self.max_value)
            dots = int(self.value * self.print_width / self.max_value)
            bar = "{nl}[{c}{nc}] {p}% ".format(
                c="+" * dots, nc="." * (self.print_width - dots), p=percent,
                nl=self.newline)
            sys.stdout.write(bar)
            sys.stdout.flush()


if __name__ == "__main__":
    p = ProgressBar()
    for i in range(0, 100):
        p.update(value=i)
        time.sleep(0.05)
    p.finish()
