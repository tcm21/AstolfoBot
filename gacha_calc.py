from scipy.stats import binom

import cvxpy

def get_percentage_text(value: int) -> str:
    return f'{remove_zeros_decimal("{:.2f}".format(value * 100))}%'


def remove_zeros_decimal(value):
    return str(value).rstrip("0").rstrip(".") if "." in str(value) else str(value)


QUARTZ_PACKS = [
    (10000, 168),
    (4900, 77),
    (2940, 41),
    (1480, 19),
    (490, 5),
    (120, 1),
]


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

    quartzes = [pack[1] for pack in QUARTZ_PACKS]
    yen = [pack[0] for pack in QUARTZ_PACKS]
    selection = cvxpy.Variable(len(quartzes), integer=True)

    constraints = [
        selection >= 0,
        selection @ quartzes >= number_of_quartz
    ]
    
    total_yen = selection @ yen

    prob = cvxpy.Problem(cvxpy.Minimize(total_yen), constraints)
    prob.solve(solver=cvxpy.GLPK_MI)

    if prob.status == "optimal":
        result_text.append("\n**Amount of money needed**:")
        total_money = 0
        total_quartz = 0
        for idx, value in enumerate(selection.value):
            if value == 0:
                continue
            result_text.append(f'{QUARTZ_PACKS[idx][0]} ({int(QUARTZ_PACKS[idx][1])}) x {int(value)} = {int(QUARTZ_PACKS[idx][1] * value)} quartz')
            total_money += QUARTZ_PACKS[idx][0] * value
            total_quartz += QUARTZ_PACKS[idx][1] * value
        result_text.append(f"**Total**: {int(total_quartz)} quartz ({int(total_money)} yen)")

    return "\n".join(result_text)
