from scipy.stats import binom


def get_percentage_text(value: int) -> str:
    return f'{remove_zeros_decimal("{:.2f}".format(value * 100))}%'


def remove_zeros_decimal(value):
    return str(value).rstrip("0").rstrip(".") if "." in str(value) else str(value)


def roll(number_of_quartz: int, number_of_tickets: int, p: float = 0.008) -> str:
    n = 0
    for i in range(int(number_of_quartz / 30)):
        n += 11
    remaining_quartz = number_of_quartz % 30
    n += int(remaining_quartz / 3)

    for i in range(int(number_of_tickets / 10)):
        n += 11
    n += number_of_tickets % 10
    result_text = []
    if number_of_quartz > 0: result_text.append(f'**Number of quartz:** {number_of_quartz}')
    if number_of_tickets > 0: result_text.append(f'**Number of tickets:** {number_of_tickets}')
    result_text.append(f'**Rolls:** {n}')
    result_text.append(f'**Probability:** {get_percentage_text(p)}\n')
    r_values = list(range(n + 1))
    dist = [binom.pmf(r, n, p) for r in r_values ]
    for i in range(n + 1):
        if i == 0:
            text = f'**NP{str(r_values[i])}:** {get_percentage_text(dist[i])}'
            result_text.append(text)
            continue
        if i > 5: continue
        sum = 0
        for j in range(i, n + 1):
            sum += dist[j]
        text = f'**NP{str(r_values[i])}+:** {get_percentage_text(sum)}'
        result_text.append(text)

    result_text.append(f'\nNumber of yukichis needed: {int(number_of_quartz / 168) + (1 if number_of_quartz > 0 else 0)}')
    return "\n".join(result_text)
