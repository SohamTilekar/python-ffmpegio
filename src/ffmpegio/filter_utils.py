from collections.abc import Sequence
import re


def compose_filter(name, *args, id=None, **kwargs):
    """Compose FFmpeg filter expression

    :param name: filter name
    :type name: str
    :param *args: option value sequence
    :type *args: seq of stringifyable items
    :param **kwargs: option key-value pairs
    :type **kwargs: dict of stringifyable values
    :param id: optional filter id, defaults to None
    :type id: str, optional
    :return: filter expression
    :rtype: str

    :note: automatically apply string escaping
    """

    # FILTER_ARGUMENTS ::= sequence of chars (possibly quoted)
    # FILTER           ::= [LINKLABELS] FILTER_NAME ["=" FILTER_ARGUMENTS] [LINKLABELS]
    #
    # filter_name is the name of the filter class of which the described filter is an instance of,
    # and has to be the name of one of the filter classes registered in the program optionally
    # followed by "@id". The name of the filter class is optionally followed by a string "=arguments".
    # arguments is a string which contains the parameters used to initialize the filter instance.
    #
    # If the option value itself is a list of items, the items in the list are usually separated by ‘|’.
    #
    # It may have one of two forms:
    # - ’:’-separated list of key=value pairs.
    # - ’:’-separated list of value. In this case, the keys are assumed to be the option names in
    #   the order they are declared.
    # - ’:’-separated list of mixed direct value and long key=value pairs. The direct value must
    #   precede the key=value pairs, and follow the same constraints order of the previous point.
    #   The following key=value pairs can be set in any preferred order.

    # if len(args) > keylist[0] or set(kwargs.keys()) > set(keylist[1:]):
    #     raise Exception(
    #         "Unsupported number of arguments or invalid argument keys given"
    #     )

    if id is not None:
        name = f"{name}@{id}"

    if not (len(args) or len(kwargs)):
        return name

    def finalize_option_value(value):
        # flatten a sequence and add escaping to ' and \
        # A first level escaping affects the content of each filter option value, which may contain
        # the special character : used to separate values, or one of the escaping characters \'.
        if not isinstance(value, str) and isinstance(value, Sequence):
            value = "|".join(str(value))
        elif isinstance(value, bool):
            value = str(value).lower()

        value = (
            re.sub(r"(['\\:])", r"\\\1", value)
            if isinstance(value, str)
            else str(value)
        )

        return value if set("[],;':\\ ").isdisjoint(set(value)) else f"'{value}'"

    args = [finalize_option_value(i) for i in args]
    kwargs = [f"{k}={finalize_option_value(v)}" for k, v in kwargs.items()]
    arguments = ":".join(args + kwargs)

    # A second level escaping affects the whole filter description, which may contain the
    # escaping characters \' or the special characters [],; used by the filtergraph description.
    return re.sub(r"([\\\[\];,])", r"\\\1", f"{name}={arguments}")


def compose_chain(*filters, head_label=None, tail_label=None):
    """Compose fitler chain
    :param *filters: a sequence defining filters, which defines the chain in
                     the order presented. Each item must adhere to
                     `compose_filter()` arguments, except for the last, which
                     can be a dict to specify the keyword arguments.
    :param head_label: label or labels (if more than 1 pad present) for the
                       input pads of the first elements, defaults to None
    :type head_label: str or seq of str, optional
    :param tail_label: label or labels (if more than 1 pad present) for the
                       output pads of the last filter, defaults to None
    :type tail_label: str or seq of str, optional
    :return: filter graph expression
    :rtype: str
    """

    def define_filter(info):

        if isinstance(info, str):
            return info

        has_kw = isinstance(info[-1], dict)
        kwargs = info[-1] if has_kw else {}
        return compose_filter(*(info[:-1] if has_kw else info), **kwargs)

    chain = ",".join([define_filter(info) for info in filters])

    if isinstance(head_label, str):
        chain = f"[{head_label}]{chain}"
    elif isinstance(head_label, Sequence):
        chain = "".join([f"[{label}]" for label in head_label]) + chain

    if isinstance(tail_label, str):
        chain = f"{chain}[{tail_label}]"
    elif isinstance(head_label, Sequence):
        chain += "".join([f"[{label}]" for label in tail_label])

    return chain


def compose_graph(*chains, input_labels={}, output_labels={}):
    """Compose complex filter graph
    :param *chains: a sequence defining filter chains which comprise the
                    graph. First item is a sequence to be directly sent to
                    `compose_chain()` and other items (if present) defines
                    the links from the output pads of the last filter
                    elements of the chains. If a chain only outputs,
                    specify no link and set its label using `output_labels`
                    argument below.
    :type chains[]: seq
    :param input_labels: specifies input streams to the graph. Keys are
                         stream specifiers and values are sequences of
                         (chain_id, in_pad_id) of the receiving chains, defaults to {}
    :type input_labels: dict, optional
    :param output_labels: specifies output streams from the graph. Keys are
                          string labels and values are chain index and
                          output pads of the last filter, defaults to {}
    :type output_labels: dict, optional
    :returns: filter graph expression
    :rtype: str
    """

    nchains = len(chains)
    cids = range(nchains)

    print(chains, input_labels, output_labels)

    def set_pad_label(defs, p, label=None):
        no_pad = isinstance(p, int)
        cid = p if no_pad else p[0]
        pad = 0 if no_pad else p[1]

        def default_label():
            return f"L{cid}_{pad}"

        if label is None:
            label = default_label()
        if cid not in defs:
            defs[cid] = {pad: label}
        elif pad not in defs[cid]:
            defs[cid][pad] = label
        elif label != default_label():
            raise Exception(
                f"duplicate filter pad labels found for chain #{cid}: {defs[cid][pad]}, {label}"
            )
        return label

    # define input pads of all chains
    input_defs = {}
    for label, p in input_labels.items():
        set_pad_label(input_defs, p, label)

    # define output pads of all chains
    output_defs = {}
    for label, p in output_labels.items():
        set_pad_label(output_defs, p, label)

    # add linking labels
    for i in cids:
        # get defined links
        links = chains[i][1:]
        nlinks = len(links)
        if not nlinks:
            continue

        for j in range(nlinks):
            # set source pad label
            label = set_pad_label(output_defs, (i, j))

            # set dest pad labels
            for p in links[j]:
                set_pad_label(input_defs, p, label)

    # finalize labels of chain input/ourput
    def finalize_labels(defs):
        return [defs.get(i, "") for i in range(len(defs))]

    return ";".join(
        [
            compose_chain(
                *((chain,) if isinstance((chain := chains[i][0]), str) else chain),
                head_label=finalize_labels(input_defs.get(i, {})),
                tail_label=finalize_labels(output_defs.get(i, {})),
            )
            for i in cids
        ]
    )


def parse_graph(expr):
    chains = re.split(r"(?<!\\);", expr)
    in_labels = {}
    out_labels = {}
    for i, chain in enumerate(chains):
        chain = chains[i]
        m = re.match(r"(\s*\[.*?\]\s*)+", chain)
        if m:
            labels = re.split(r"\]\[", m[0][1:-1])
            in_labels = {**in_labels, **{v: (i, j) for j, v in enumerate(labels)}}
            chain = chain[m.end(0) :]
        m = re.match(r"(\s*\[.*?\]\s*)+$", chain)
        if m:
            labels = re.split(r"\]\s*\[", m[0][1:-1])
            out_labels = {**out_labels, **{v: (i, j) for j, v in enumerate(labels)}}
            chain = chain[: m.start(0)]
        chains[i] = chain
    return [(chain,) for chain in chains], {
        "input_labels": in_labels,
        "output_labels": out_labels,
    }


def trace_graph_downstream(labels, start_label, allow_split=True):

    outputs = labels["output_labels"]
    inputs = labels["input_labels"]

    def get_cid(link):
        return link and link if isinstance(link, int) else link[0]

    next_link = start_label
    while next_link in inputs:
        next_chain = get_cid(inputs[next_link])
        if next_chain is None:
            raise Exception("invalid filter graph (missing input link info)")
        next_links = [(l for l, v in outputs.items() if get_cid(v) == next_chain)]
        nlinks = len(next_links)
        if nlinks < 1:
            raise Exception("invalid filter graph (missing output link)")
        elif nlinks < 2:
            next_link = next_links[0]
        elif allow_split:
            out_labels = []
            for label in next_links:
                out_labels.extend(trace_graph_downstream(labels, label, True))
            return out_labels
        else:
            raise Exception("split in filter graph found")
    return [next_link] if allow_split else next_link


def get_chain_labels(labels, id):
    """get labels associated with the chain id, sorted by their pad ids

    :param labels: label names as keys and chain id and optionally pad id as values: str:int or str:(int,int)
    :type labels: dict
    :param id: chain id
    :type id: int
    :return: stream specifiers, in the pad id order
    :rtype: list of str
    """
    return [
        spec
        for _, spec in sorted(
            [
                (0 if isinstance(v, int) else v[1], k)
                for k, v in labels.items()
                if (v == id if isinstance(v, int) else v[0] == id)
            ]
        )
    ]


def extend_chain(chains, labels, new_chain, insert_at, keep_output_label=True):

    outputs = labels["output_labels"]
    inputs = labels["input_labels"]
    src = outputs.get(insert_at, None)
    dst = inputs.get(insert_at, None)

    cid = len(chains)
    new_label = f"L{cid}"

    chains.append(new_chain)
    if keep_output_label or src is None:
        outputs[new_label] = cid
        inputs[new_label] = dst
        if src is not None:
            inputs[insert_at] = cid
    else:
        inputs[new_label] = cid
        outputs[new_label] = src
        if dst is not None:
            outputs[insert_at] = cid