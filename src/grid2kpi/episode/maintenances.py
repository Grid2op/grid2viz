
def nb_maintenances(episode):
    # Suppose that there is at most one maintenance per line per episode

    return sum(
        1 for t in episode.observations[0].duration_next_maintenance if t
    )


def duration_maintenances(epsiode):
    # Suppose that there is at most one maintenance per line per episode

    return sum(
        t for t in epsiode.observations[0].duration_next_maintenance if t
    )


def hist_duration_maintenances(episode):
    # Suppose that there is at most one maintenance per line per episode

    return [t for t in episode.observations[0].duration_next_maintenance if t]