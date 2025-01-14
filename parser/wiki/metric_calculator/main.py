from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
import numpy as np
import os
import sys


@dataclass
class ParserStats:
    CLIPAvgTime: float = 0
    CLIPErrorRatio: float = 0
    CLIPEmptyRatio: float = 0
    CLIPP99Time: float = 0
    DocsRedirectionRatio: float = 0
    DocsParsed: int = 0
    DurationAvg: float = 0
    DurationMax: float = 0
    DurationP99: float = 0
    ImagesErrorRatio: float = 0
    ImagesParsed: int = 0
    TextErrorRatio: float = 0
    TextAvgTime: float = 0
    TextEmptyRatio: float = 0
    TextP99Time: float = 0
    TimeFirstParsed: str = ""
    TimeLastParsed: str = ""

    def __str__(self) -> str:
        return (
            f"--- Parser ---\n"
            f"Parsed docs: {self.DocsParsed}\n"
            f"Redirection ratio: {self.DocsRedirectionRatio * 100:.2f}%\n"
            f"Parsed images: {self.ImagesParsed}\n"
            f"Images error ratio: {self.ImagesErrorRatio * 100:.2f} %\n"
            f"Duration: avg = {self.DurationAvg:.2f}s, "
            f"p99 = {self.DurationP99:.2f}s, max = {self.DurationMax:.2f}s\n"
            f"First parsed time: {self.TimeFirstParsed[:-3]}\n"
            f"Last parsed time: {self.TimeLastParsed[:-3]}\n"
            f"---- CLIP ----\n"
            f"Request time: avg = {self.CLIPAvgTime:.2f}s, "
            f"p99 = {self.CLIPP99Time:.2f}s\n"
            f"Empty request ratio: {self.CLIPEmptyRatio * 100:.2f}%\n"
            f"Error ratio: {self.CLIPErrorRatio * 100:.2f}%\n"
            f"---- Text ----\n"
            f"Request time: avg = {self.TextAvgTime:.2f}s, "
            f"p99 = {self.TextP99Time:.2f}s\n"
            f"Empty request ratio: {self.TextEmptyRatio * 100:.2f}%\n"
            f"Error ratio: {self.TextErrorRatio * 100:.2f}%\n"
        )


@dataclass
class WriterStats:
    DocSizeAvg: float = 0
    DocSizeMax: int = 0
    DocSizeP99: float = 0
    WriteAmount: int = 0
    WriteErrorRatio: float = 0
    WriteFirst: str = ""
    WriteLast: str = ""

    def __str__(self) -> str:
        return (
            f"--- Writer ---\n"
            f"Docs amount: {self.WriteAmount}\n"
            f"Doc size: avg = {self.DocSizeAvg:.2f}, "
            f"p99 = {self.DocSizeP99:.2f}, max = {self.DocSizeMax}\n"
            f"Error ratio: {self.WriteErrorRatio * 100:.2f}%\n"
            f"First write time: {self.WriteFirst[:-3]}\n"
            f"Last write time: {self.WriteLast[:-3]}\n"
        )


def calculate_parser_stats(log_dir: List[str]) -> ParserStats:
    stats = ParserStats()
    parse_times: List[float] = []
    clip_times: List[float] = []
    text_times: List[float] = []
    first_time: Optional[datetime] = None
    last_time: Optional[datetime] = None

    for log_file in log_dir:
        with open(log_file) as log:
            for line_raw in log:
                try:
                    line = line_raw.strip()
                    if not line[:4].isdigit():
                        continue

                    if "to parse" in line:
                        stats.DocsParsed += 1
                        parse_times.append(float(line.split()[-3][:-1]))

                        parsed_time = datetime.strptime(
                            " ".join(line.split()[:2]),
                            "%Y-%m-%d %H:%M:%S,%f"
                        )
                        if first_time is None or parsed_time < first_time:
                            first_time = parsed_time
                        if last_time is None or parsed_time > last_time:
                            last_time = parsed_time

                    if "Page is a redirection" in line:
                        stats.DocsParsed += 1
                        stats.DocsRedirectionRatio += 1

                    if "Successfully parsed image" in line:
                        stats.ImagesParsed += 1

                    if "While parsing image" in line or "While downloading image" in line:
                        stats.ImagesErrorRatio += 1
                        stats.ImagesParsed += 1
                    
                    if "Request to CLIP server took" in line:
                        clip_times.append(float(line.split()[-1][:-1]))
                    
                    if "Request to text model server took" in line:
                        text_times.append(float(line.split()[-1][:-1]))
                    
                    if "While applying CLIP" in line:
                        stats.CLIPErrorRatio += 1

                    if "While applying text model" in line:
                        stats.TextErrorRatio += 1

                    if "Empty web enrichment CLIPEnrichment" in line:
                        stats.CLIPEmptyRatio += 1

                    if "Empty web enrichment TextEnrichment" in line:
                        stats.TextEmptyRatio += 1
                except Exception:
                    continue

    stats.CLIPEmptyRatio /= len(clip_times)
    stats.CLIPErrorRatio /= (stats.CLIPErrorRatio + len(clip_times))
    stats.CLIPAvgTime = np.mean(clip_times).item()
    stats.CLIPP99Time = np.quantile(clip_times, 0.99).item()
    stats.DocsRedirectionRatio /= stats.DocsParsed
    stats.DurationAvg = np.mean(parse_times).item()
    stats.DurationP99 = np.quantile(parse_times, 0.99).item()
    stats.DurationMax = np.max(parse_times).item()
    stats.ImagesErrorRatio /= stats.ImagesParsed
    stats.TextEmptyRatio /= len(text_times)
    stats.TextErrorRatio /= (stats.TextErrorRatio + len(text_times))
    stats.TextAvgTime = np.mean(text_times).item()
    stats.TextP99Time = np.quantile(text_times, 0.99).item()
    if first_time is not None:
        stats.TimeFirstParsed = datetime.strftime(first_time, "%Y-%m-%d %H:%M:%S,%f")
    if last_time is not None:
        stats.TimeLastParsed = datetime.strftime(last_time, "%Y-%m-%d %H:%M:%S,%f")

    return stats


def calculate_writer_stats(log_dir: List[str]) -> WriterStats:
    stats = WriterStats()
    doc_sizes: List[int] = []
    first_time: Optional[datetime] = None
    last_time: Optional[datetime] = None

    for log_file in log_dir:
        with open(log_file) as log:
            for line_raw in log:
                try:
                    line = line_raw.strip()
                    if not line[:4].isdigit():
                        continue

                    if "Writing page" in line:
                        stats.WriteAmount += 1
                        doc_sizes.append(int(line.split()[-1][:-1]))

                        parsed_time = datetime.strptime(
                            " ".join(line.split()[:2]),
                            "%Y-%m-%d %H:%M:%S,%f"
                        )
                        if first_time is None or parsed_time < first_time:
                            first_time = parsed_time
                        if last_time is None or parsed_time > last_time:
                            last_time = parsed_time

                    if "While writing page" in line:
                        stats.WriteErrorRatio += 1
                except Exception:
                    continue

    stats.DocSizeAvg = np.mean(doc_sizes).item()
    stats.DocSizeP99 = np.quantile(doc_sizes, 0.99).item()
    stats.DocSizeMax = np.max(doc_sizes).item()
    stats.WriteErrorRatio /= stats.WriteAmount
    if first_time is not None:
        stats.WriteFirst = datetime.strftime(first_time, "%Y-%m-%d %H:%M:%S,%f")
    if last_time is not None:
        stats.WriteLast = datetime.strftime(last_time, "%Y-%m-%d %H:%M:%S,%f")

    return stats


if __name__ == '__main__':
    log_dir = sys.argv[1]
    log_files = os.listdir(log_dir)

    writer_logs = [
        os.path.join(log_dir, file_name)
        for file_name in log_files
        if file_name.split('/')[-1] == 'output_writer.log'
    ]
    parser_logs = [
        os.path.join(log_dir, file_name)
        for file_name in log_files
        if (
            file_name.split('/')[-1].startswith('output_') and
            file_name.split('/')[-1].endswith('.log') and
            file_name not in writer_logs
        )
    ]

    sys.stdout.write(str(calculate_parser_stats(parser_logs)))
    sys.stdout.write(str(calculate_writer_stats(writer_logs)))
