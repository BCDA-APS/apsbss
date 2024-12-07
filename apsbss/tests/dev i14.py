from apsbss.bss_is import IS_SchedulingServer
from apsbss.tests._core import CREDS_FILE
import yaml


def main():
    ss = IS_SchedulingServer()
    ss.auth_from_file(CREDS_FILE)

    # station, run = "8-ID-I", "2022-2"
    # print(f"{ss.proposals(station, run)=}")

    # for station in "8-ID-E 8-ID-I 12-ID-E".split():
    #     for run in "2022-1 2022-2 2022-3 2023-1 2023-2 2023-3 2024-1 2024-2 2024-3".split():
    #         try:
    #             activities = ss.activities(station, run)
    #             print(f"{station!r} {run!r} {len(activities)=}")
    #         except Exception as reason:
    #             print(f"{station!r} {run!r} {reason=}")

    # print(f"{len(ss.activities('8-ID-E', '2022-1'))=}")
    # print(f"{len(ss.proposals('8-ID-E', '2022-1'))=}")
    # print(f"{len(ss.activities('8-ID-I', '2022-1'))=}")
    # print(f"{len(ss.proposals('8-ID-I', '2022-1'))=}")

    station, run, gup = "8-ID-E", "2022-1", 78544
    station, run, gup = "8-ID-I", "2022-1", 78243
    # fmt: off
    activities = ss.activities(station, run)
    # fmt: on
    proposals = ss.proposals(station, run)

    joint = sorted(
        set(
            [
                gup
                for gup in list(activities.keys()) + list(proposals.keys())
                if gup in activities and gup in proposals
            ]
        )
    )

    for gup in joint:
        if "@anl.gov" in proposals[gup].pi:
            print(proposals[gup])

    gup = joint[-1]
    gup = 78243

    print(yaml.dump(dict(activities[gup])))
    print("-" * 40)
    print(yaml.dump(dict(proposals[gup].raw)))


if __name__ == "__main__":
    main()
