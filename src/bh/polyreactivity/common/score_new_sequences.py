import importlib.resources as pkg_resources
import pickle
import re
import warnings

import bh.polyreactivity.models as models
import numpy as np
import pandas as pd
from Bio.SeqUtils.ProtParam import ProteinAnalysis
from bh.biocore.sequences.number import convert_sequences_to_numbered_frame
from bh.polyreactivity.common.double_mutant_generation import generate_doubles
from bh.polyreactivity.common.models import CNN, RNN
from bh.polyreactivity.common.utils import (
    return_scores,
)

warnings.filterwarnings("ignore")

"""
script intakes a one sequence csv created by ANARCI/IMGT and outputs all possible double mutants
"""
aa_list = np.asarray(list("ACDEFGHIKLMNPQRSTVWY-"))


def example_function(seq):
    return f"The sequence is: {seq}"


def get_kmer_list(seq, include_framework="", kmer_len=3):
    if "C" in include_framework:
        seq = "C" + seq
    if "W" in include_framework:
        seq = seq + "W"
    kmer_counts = {}
    k = 1
    while k <= kmer_len:
        num_chunks = (len(seq) - kmer_len) + 1
        for idx in range(0, num_chunks):
            kmer = seq[idx : idx + kmer_len]
            assert len(kmer) == kmer_len
            if kmer in kmer_counts:
                kmer_counts[kmer] += 1
            else:
                kmer_counts[kmer] = 1
        k += 1
    return [(key, val) for key, val in kmer_counts.items()]


def cdr_seqs_to_kmer(seqs, include_framework="", k=3):
    seq_to_kmer_vector = {}
    aa_list = "ACDEFGHIKLMNPQRSTVWY"
    kmer_list = [aa for aa in aa_list]
    i = 1
    last_kmer_list = kmer_list
    while i < k:
        more_kmer_list = []
        for ii in last_kmer_list:
            for aa in aa_list:
                more_kmer_list.append(ii + aa)
        kmer_list.extend(more_kmer_list)
        last_kmer_list = more_kmer_list
        i += 1
    kmer_to_idx = {aa: i for i, aa in enumerate(kmer_list)}
    for seq in seqs:
        # Make into kmers
        kmer_data_list = get_kmer_list(seq, include_framework=include_framework, kmer_len=k)
        # print(len(kmer_data_list))

        norm_val = 0.0
        for kmer, count in kmer_data_list:
            count = float(count)
            norm_val += count  # norm
            # norm_val += (count * count) L2 norm
        # norm_val = np.sqrt(norm_val) L2 norm

        # L2 normalize
        final_kmer_data_list = []
        for kmer, count in kmer_data_list:
            final_kmer_data_list.append((kmer_to_idx[kmer], float(count) / norm_val))

        # save to a dictionary
        seq_to_kmer_vector[seq] = final_kmer_data_list

    kmer_arr = np.zeros((len(seqs), len(kmer_to_idx)), dtype=np.float32)
    for i, seq in enumerate(seqs):
        kmer_vector = seq_to_kmer_vector[seq]
        for j_kmer, val in kmer_vector:
            kmer_arr[i, j_kmer] = val
    return kmer_arr


def one_hot_3D(s):
    """Transform sequence string into one-hot aa vector"""
    # One-hot encode as row vector
    aa_list = "ACDEFGHIKLMNPQRSTVWY"
    aa_dict = {}
    for i, aa in enumerate(aa_list):
        aa_dict[aa] = i
    x = np.zeros((len(s), len(aa_list)))
    for i, letter in enumerate(s):
        if letter in aa_dict:
            x[i, aa_dict[letter]] = 1
    return x


def cdr_seqs_to_onehot(seqs):
    aa_list = "ACDEFGHIKLMNPQRSTVWY"
    aa_dict = {}
    for i, aa in enumerate(aa_list):
        aa_dict[aa] = i
    onehot_array = np.empty((len(seqs), len(seqs.iloc[0]), 20))
    for s, seq in enumerate(seqs):
        if len(seq) != onehot_array.shape[1]:
            continue
        onehot_array[s] = one_hot_3D(seq)
    onehot_array = onehot_array.reshape(len(seqs), -1)
    onehot_array[np.isnan(onehot_array)] = 0
    return onehot_array


def withgap_CDR3(seq):
    if type(seq) == float:
        return ""
    if len(seq) < 22:
        nogap_seq = seq.replace("-", "")
        if len(nogap_seq) % 2 == 0:
            gap_seq = nogap_seq[: len(nogap_seq) // 2] + "-" * (22 - len(nogap_seq)) + nogap_seq[-len(nogap_seq) // 2 :]
        else:
            gap_seq = (
                nogap_seq[: len(nogap_seq) // 2 + 1] + "-" * (22 - len(nogap_seq)) + nogap_seq[-(len(nogap_seq) // 2) :]
            )
    else:
        gap_seq = seq[:11] + seq[-11:]
    return gap_seq


kd = {
    "A": 1.8,
    "R": -4.5,
    "N": -3.5,
    "D": -3.5,
    "C": 2.5,
    "Q": -3.5,
    "E": -3.5,
    "G": -0.4,
    "H": -3.2,
    "I": 4.5,
    "L": 3.8,
    "K": -3.9,
    "M": 1.9,
    "F": 2.8,
    "P": -1.6,
    "S": -0.8,
    "T": -0.7,
    "W": -0.9,
    "Y": -1.3,
    "V": 4.2,
}


def hp_index(seq, kd=kd):
    hp_ix = 0
    for a in seq:
        hp_ix += kd[a]
    return hp_ix / len(seq)


N_glycosylation_pattern = "N[^P][ST][^P]"

# N-linked glycosylation
def find_glyc(seq):
    if re.search(N_glycosylation_pattern, seq):
        return True
    else:
        return False


def extract_cdrs(old_df):
    df = pd.DataFrame()
    df["full_sequence"] = old_df.groupby(["i"]).aa.apply(lambda x: "".join(x))
    df["CDR1_withgaps"] = (
        old_df.query("kabat_index >= 27 and kabat_index <= 38")
        .fillna("-")
        .groupby(["i"])
        .aa.apply(lambda x: "".join(x))
    )
    df["CDR2_withgaps"] = (
        old_df.query("kabat_index >= 55 and kabat_index <= 65")
        .fillna("-")
        .groupby(["i"])
        .aa.apply(lambda x: "".join(x))
    )
    df["CDR2_withgaps_full"] = (
        old_df.query("kabat_index >= 55 and kabat_index <= 66")
        .fillna("-")
        .groupby(["i"])
        .aa.apply(lambda x: "".join(x))
    )
    df["CDR3_withgaps"] = (
        old_df.query("kabat_index >= 105 and kabat_index <= 117")
        .fillna("-")
        .groupby(["i"])
        .aa.apply(lambda x: "".join(x))
    )

    df["CDRS_withgaps"] = df["CDR1_withgaps"] + df["CDR2_withgaps"] + df["CDR3_withgaps"]
    df["CDR1_withgaps"] = df["CDR1_withgaps"].str[:4] + df["CDR1_withgaps"].str[-4:]
    df["CDR2_withgaps"] = df["CDR2_withgaps"].str[:5] + df["CDR2_withgaps"].str[-4:]
    df["CDR2_withgaps_full"] = df["CDR2_withgaps_full"].str[:5] + df["CDR2_withgaps_full"].str[-5:]
    df["CDR3_withgaps"] = df["CDR3_withgaps"].apply(withgap_CDR3)

    df["CDR1_nogaps"] = df["CDR1_withgaps"].str.replace("-", "")
    df["CDR2_nogaps"] = df["CDR2_withgaps"].str.replace("-", "")
    df["CDR3_nogaps"] = df["CDR3_withgaps"].str.replace("-", "")
    df["CDR2_nogaps_full"] = df["CDR2_withgaps_full"].str.replace("-", "")

    df["CDRS_nogaps"] = df["CDR1_nogaps"] + df["CDR2_nogaps"] + df["CDR3_nogaps"]
    df["CDRS_nogaps_full"] = df["CDR1_nogaps"] + df["CDR2_nogaps_full"] + df["CDR3_nogaps"]
    df["CDRS_withgaps"] = df["CDR1_withgaps"] + df["CDR2_withgaps"] + df["CDR3_withgaps"]
    df["CDRS_withgaps_full"] = df["CDR1_withgaps"] + df["CDR2_withgaps_full"] + df["CDR3_withgaps"]
    return df


def get_summary_statistics(df):
    df["isoelectric point"] = df["CDRS_nogaps"].apply(lambda x: ProteinAnalysis(x).isoelectric_point())
    df["hydrophobicity"] = df["CDRS_nogaps"].apply(hp_index)
    df["CDR1_length"] = df["CDR1_nogaps"].str.len()
    df["CDR2_length"] = df["CDR2_nogaps"].str.len()
    df["CDR3_length"] = df["CDR3_nogaps"].str.len()
    df["CDR1_glycosylation"] = df["CDR1_nogaps"].apply(lambda x: find_glyc(x))
    df["CDR2_glycosylation"] = df["CDR2_nogaps"].apply(lambda x: find_glyc(x))
    df["CDR3_glycosylation"] = df["CDR3_nogaps"].apply(lambda x: find_glyc(x))
    return df


def read_fa(fa_file):
    """reads fasta file into header/sequence pairs"""
    header = ""
    seq = ""
    seqs = []
    with open(fa_file, "r") as f:
        for line in f:
            line = line.strip()
            if len(line) == 0 or line[0] == "#":
                continue
            if line[0] == ">":
                seqs.append((header, seq))
                header = line[1:]
                seq = ""
            else:
                seq += line
    seqs.append((header, seq))
    seqs = pd.DataFrame(seqs[1:], columns=["header", "seq"])
    return seqs


def rank_and_filter_columns(df):
    df_wt = df.iloc[0]
    df_ranked = df.iloc[1:].sort_values("origFACS lr onehot", ascending=False)
    return pd.concat([df_wt.to_frame().T, df_ranked]).iloc[:31]


def score_sequences(
    sequence_list: list[str],
    doubles: bool = False,
):
    numbered_sequences = convert_sequences_to_numbered_frame(sequence_list)
    df = extract_cdrs(numbered_sequences)
    if doubles and len(df) == 1:
        df = generate_doubles(df.copy())
    # Only keep CDRs of the appropriate length for the models
    df = df[~df["CDRS_nogaps"].isnull()]
    df = df[df["CDRS_withgaps"].apply(lambda x: len(x) == 39)]
    df = get_summary_statistics(df.copy())

    # log reg
    m = pickle.load(pkg_resources.open_binary(models, "logistic_regression_onehot_CDRS.sav"))
    X_test = cdr_seqs_to_onehot(df["CDRS_withgaps"])
    assert (
        X_test.shape[1] == m.coef_.shape[1]
    ), f"Shape of the one-hot data {X_test.shape[1]} doesn't match the model coefficients {m.coef_.shape[1]}"

    y_score = m.decision_function(X_test)
    df["origFACS lr onehot"] = y_score
    batch_size = 1024

    # log reg with 3mers
    m = pickle.load(pkg_resources.open_binary(models, "logistic_regression_3mer_CDRS.sav"))
    if len(df) < batch_size:
        X_test = cdr_seqs_to_kmer(df["CDRS_nogaps"])
        y_score = m.decision_function(X_test)
        df["origFACS lr 3mers"] = y_score
    else:
        df["origFACS lr 3mers"] = np.nan
        for batch_tick in np.append(np.arange(batch_size, len(df), batch_size), len(df)):
            X_test = cdr_seqs_to_kmer(df["CDRS_nogaps"].iloc[batch_tick - batch_size : batch_tick], k=3)
            y_score = m.decision_function(X_test)
            df["origFACS lr 3mers"].iloc[batch_tick - batch_size : batch_tick] = y_score

    # CNN full
    model = CNN(input_size=7)
    filepath = pkg_resources.open_binary(models, "cnn_full_20.tar")
    df["origFACS cnn onehot"] = return_scores(df, model, filepath)

    # RNN full
    model = RNN(input_size=20, hidden_size=128, num_layers=2, num_classes=1)
    filepath = pkg_resources.open_binary(models, "rnn_full_20.tar")
    df["origFACS rnn onehot"] = return_scores(df, model, filepath, region="CDRS_nogaps", model_type="rnn", max_len=39)

    # RNN full long
    filepath = pkg_resources.open_binary(models, "rnn_CDRS_full_dist0_20.tar")
    df["deepFACS rnn onehot"] = return_scores(
        df, model, filepath, region="CDRS_nogaps_full", model_type="rnn", max_len=40
    )

    # CNN full long
    model = CNN(input_size=8)
    filepath = pkg_resources.open_binary(models, "cnn_CDRS_full_dist0_10.tar")
    df["deepFACS cnn onehot"] = return_scores(df, model, filepath, region="CDRS_withgaps_full")

    # logreg 3mers full
    m = pickle.load(pkg_resources.open_binary(models, "3mer_logistic_regression_CDRS_full_dist0.sav"))
    if len(df) < batch_size:
        X_test = cdr_seqs_to_kmer(df["CDRS_nogaps_full"])
        y_score = m.decision_function(X_test)
        df["deepFACS lr 3mer"] = y_score
    else:
        df["deepFACS lr 3mer"] = np.nan
        for batch_tick in np.append(np.arange(batch_size, len(df), batch_size), len(df)):
            X_test = cdr_seqs_to_kmer(df["CDRS_nogaps_full"].iloc[batch_tick - batch_size : batch_tick], k=3)
            y_score = m.decision_function(X_test)
            df["deepFACS lr 3mer"].iloc[batch_tick - batch_size : batch_tick] = y_score

    # logreg full
    m = pickle.load(pkg_resources.open_binary(models, "onehot_logistic_regression_CDRS_full_dist0.sav"))
    X_test = cdr_seqs_to_onehot(df["CDRS_withgaps_full"])
    y_score = m.decision_function(X_test)
    df["deepFACS lr onehot"] = y_score

    return df
