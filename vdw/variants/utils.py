import hashlib
from vcf.model import _Record

MD5_ARG_DELIMITER = '|'


def calculate_md5(*args, **kwargs):
    alt_index = alt_value = None
    if 'alt_value' in kwargs:
        alt_value = kwargs['alt_value']
    if 'alt_index' in kwargs:
        alt_index = kwargs['alt_index']
    if alt_value and alt_index:
        raise ValueError("Both alt_value and alt_index were supplied when "
                         "calculating a hash.  The alternate allele should "
                         "be identified using only one of these methods.")
    if len(args) == 1 and isinstance(args[0], _Record):
        r = args[0]

        if not alt_value:
            if alt_index:
                alt_value = r.ALT[alt_index]
            else:
                alt_value = ','.join([str(x) for x in r.ALT])
        values = [r.CHROM, r.POS, r.REF, alt_value]
    elif len(args) == 4:
        values = list(args)
    else:
        raise ValueError('Invalid arguments')
    for i, value in enumerate(values):
        # Position is an int, everything else a string
        if i == 1:
            assert isinstance(value, int) or value.isdigit()
            values[i] = str(value)
        else:
            assert isinstance(value, basestring)
    return hashlib.md5(MD5_ARG_DELIMITER.join(values)).hexdigest()
