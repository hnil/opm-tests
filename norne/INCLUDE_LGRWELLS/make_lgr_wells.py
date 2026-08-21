"""Convert two Norne wells to LGR completions.

Each well sits alone in its own 3x3x22 CARFIN box, refined 3x3x1, so the well's
column is the box's centre parent cell and its LGR-local column is (5,5).  The
deck's explicit connection factors are carried over untouched: the well index
stays exactly what the history match built, and the refinement only resolves the
flow around it.
"""
import re, sys

SCH  = '/Users/hnil/Documents/OPM/opm_vscode_clean/opm-tests/norne/INCLUDE/BC0407_HIST01122006.SCH'
OUT  = '/Users/hnil/Documents/OPM/opm_vscode_clean/opm-tests/norne/INCLUDE_LGRWELLS/BC0407_HIST01122006_LGRWELLS.SCH'

# well -> (lgr name, box i1, j1, refinement in i, j)
WELLS = {'F-1H': ('LGR1', 11, 84, 3, 3),
         'E-3H': ('LGR2', 11, 72, 3, 3)}

def local(i, j, w):
    _, i1, j1, ri, rj = WELLS[w]
    # centre child column of the parent cell (i,j)
    return (i - i1) * ri + (ri + 1) // 2, (j - j1) * rj + (rj + 1) // 2

def wellname(rec):
    m = re.match(r"\s*'([^']+)'", rec)
    return m.group(1) if m else None

def split_records(body):
    """Yield (kind, text) with kind in {'rec','other'}; records end at '/'."""
    out, buf = [], ''
    for line in body.splitlines(True):
        stripped = line.split('--')[0].strip()
        if not stripped:
            out.append(('other', line)); continue
        buf += line
        if stripped.endswith('/'):
            out.append(('rec', buf)); buf = ''
    if buf:
        out.append(('other', buf))
    return out

def convert(text, kw, lgrkw, converter):
    out = []
    pos = 0
    for m in re.finditer(r'(?m)^%s\s*?$\n(.*?)^/\s*$\n' % kw, text, re.S):
        out.append(text[pos:m.start()])
        keep, moved = [], []
        for kind, chunk in split_records(m.group(1)):
            w = wellname(chunk) if kind == 'rec' else None
            if w in WELLS:
                moved.append(converter(chunk, w))
            else:
                keep.append(chunk)
        block = ''
        if any(k.strip() for k in keep):
            block += kw + '\n' + ''.join(keep) + '/\n'
        if moved:
            block += lgrkw + '\n' + ''.join(moved) + '/\n'
        out.append(block)
        pos = m.end()
    out.append(text[pos:])
    return ''.join(out)

def conv_welspecs(rec, w):
    # WELL GROUP I J ...  ->  WELL GROUP LGR I J ...
    t = rec.split()
    i, j = local(int(t[2]), int(t[3]), w)
    lgr = WELLS[w][0]
    return "     %-8s %-10s '%s' %4d %4d  %s\n" % (t[0], t[1], lgr, i, j, ' '.join(t[4:]))

def conv_compdat(rec, w):
    # WELL I J K1 K2 ...  ->  WELL LGR I J K1 K2 ...
    t = rec.split()
    i, j = local(int(t[1]), int(t[2]), w)
    lgr = WELLS[w][0]
    return "     %-8s '%s' %4d %4d %4s %4s  %s\n" % (t[0], lgr, i, j, t[3], t[4], ' '.join(t[5:]))

src = open(SCH).read()
res = convert(src, 'WELSPECS', 'WELSPECL', conv_welspecs)
res = convert(res, 'COMPDAT', 'COMPDATL', conv_compdat)
open(OUT, 'w').write(res)

print('WELSPECL records:', sum(1 for l in res.splitlines() if re.match(r"\s*'(F-1H|E-3H)'", l) and "'LGR" in l and 'OIL' in l))
print('COMPDATL blocks :', len(re.findall(r'(?m)^COMPDATL', res)))
print('WELSPECL blocks :', len(re.findall(r'(?m)^WELSPECL', res)))
print('leftover COMPDAT records naming a converted well:',
      sum(1 for b in re.findall(r'(?m)^COMPDAT\s*?$\n(.*?)^/\s*$', res, re.S)
            for l in b.splitlines() if re.match(r"\s*'(F-1H|E-3H)'", l)))
