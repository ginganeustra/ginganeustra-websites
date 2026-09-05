#!/usr/bin/env python3
from pathlib import Path

ROOT = Path("Rustler")


def patch(path: str, replacements: list[tuple[str, str]]) -> None:
    p = ROOT / path
    text = p.read_text(encoding="utf-8")
    for old, new in replacements:
        if old not in text:
            raise SystemExit(f"Expected text not found in {path}: {old[:120]!r}")
        text = text.replace(old, new)
    p.write_text(text, encoding="utf-8")
    print(f"fixed attribution: {path}")


patch("notre-dame-road-closure-council-answers-september-2026.html", [
    ("after Russell Township councillors pushed administration to come back with the costs, timing and community impact of keeping one lane open.",
     "after Russell Township councillors pushed staff to come back with the costs, timing and community impact of keeping one lane open."),
    ("<p>Staff told council Aug. 31 that excavation on the next stretch, from St-Pierre toward Domaine, is targeted to begin around Sept. 21 and run to late October. The plan presented at the meeting was to close both lanes while crews replace the watermain and storm sewer.</p>",
     "<p>Jonathan Bourgon, the Township’s executive director of planning and infrastructure services, told council Aug. 31 that excavation on the next stretch, from St-Pierre toward Domaine, is targeted to begin around Sept. 21 and run to late October. The plan presented at the meeting was to close both lanes while crews replace the watermain and storm sewer.</p>"),
    ("<p>Infrastructure staff said the fastest construction pattern is a complete closure. “To complete the work, we are planning to fully close the road again for that segment,” council was told.</p>",
     "<p>Bourgon said the fastest construction pattern is a complete closure. “To complete the work, we are planning to fully close the road again for that segment,” he told council.</p>"),
    ("<p>The complication is that the original contract was bid with one lane remaining open. Staff said requirements to protect an Enbridge gas main were added after tendering, changing how the contractor can work around the underground utilities.</p>",
     "<p>The complication is that the original contract was bid with one lane remaining open. Bourgon said requirements to protect an Enbridge gas main were added after tendering, changing how the contractor can work around the underground utilities.</p>"),
    ("<blockquote>“I’ll have to come back. I’ll have to ask the team to give me and to review all the figures.” — Township infrastructure staff</blockquote>",
     "<blockquote>“I’ll have to come back. I’ll have to ask the team to give me and to review all the figures.” — Jonathan Bourgon, executive director of planning and infrastructure services</blockquote>"),
    ("<p>Councillors also raised the effect on nearby subdivisions. If the road is completely closed, the main detour is expected to use Routes 300 and 400. Staff said it could block a residential shortcut that drivers used during an earlier closure, but doing that would also make travel less direct for people who live there.</p>",
     "<p>Councillors also raised the effect on nearby subdivisions. If the road is completely closed, the main detour is expected to use Routes 300 and 400. Bourgon said the Township could block a residential shortcut that drivers used during an earlier closure, but doing that would also make travel less direct for people who live there.</p>"),
])

patch("recreation-complex-70-million-debt-financing-september-2026.html", [
    ("<p>Administration called it “a balanced and prudent approach” that can give the Township more flexibility while reducing exposure to future interest-rate swings.</p>",
     "<p>Sébastien Dagenais, the Township’s director of corporate services and treasurer, called it “a balanced and prudent approach” that can give the Township more flexibility while reducing exposure to future interest-rate swings.</p>"),
    ("<p>Staff told council the comparison with a single long-term structure points to about $2.3 million in net interest savings during the first five years at current rates.</p>",
     "<p>Dagenais told council the comparison with a single long-term structure points to about $2.3 million in net interest savings during the first five years at current rates.</p>"),
    ("<blockquote>“The objective is to balance the opportunity presented by today’s lower short and medium term interest rate with the long term stability that taxpayers expect.” — Township administration</blockquote>",
     "<blockquote>“The objective is to balance the opportunity presented by today’s lower short and medium term interest rate with the long term stability that taxpayers expect.” — Sébastien Dagenais, director of corporate services and treasurer</blockquote>"),
    ("<p>Administration said Infrastructure Ontario’s pre-flow process normally takes six to eight weeks and requires the interest rate to be secured before council passes the final debenture bylaw. Council was told the early rate lock did not amount to approval of the whole $70-million package, although walking away from the secured financing could carry a penalty.</p>",
     "<p>Dagenais said Infrastructure Ontario’s pre-flow process normally takes six to eight weeks and requires the interest rate to be secured before council passes the final debenture bylaw. Council was told the early rate lock did not amount to approval of the whole $70-million package, although walking away from the secured financing could carry a penalty.</p>"),
])

patch("embrun-water-tower-delay-september-2026.html", [
    ("<p>Administration told council Aug. 31 that the most recent target — the end of August — has slipped by roughly a month while the contractor completes repairs and testing.</p>",
     "<p>Jonathan Bourgon, the Township’s executive director of planning and infrastructure services, told council Aug. 31 that the most recent target — the end of August — has slipped by roughly a month while the contractor completes repairs and testing.</p>"),
    ("<p>“We’re now looking at the end of September,” infrastructure staff told council. The restrictions have to remain until the tower is back online and the system is safe.</p>",
     "<p>“We’re now looking at the end of September,” Bourgon told council. The restrictions have to remain until the tower is back online and the system is safe.</p>"),
    ("<p>Staff said the job has not gone according to the original timetable. “The work to be completed did take more time and it’s more extensive than anticipated at first,” council was told.</p>",
     "<p>Bourgon said the job has not gone according to the original timetable. “The work to be completed did take more time and it’s more extensive than anticipated at first,” he told council.</p>"),
    ("<p>Administration cautioned that the fixed charge is part of the money that supports the water system whether or not residents are watering lawns. A reduction would lower the transfer to the asset-replacement reserve, creating a shortfall that would have to be made up somewhere else.</p>",
     "<p>Township staff cautioned that the fixed charge is part of the money that supports the water system whether or not residents are watering lawns. A reduction would lower the transfer to the asset-replacement reserve, creating a shortfall that would have to be made up somewhere else.</p>"),
    ("<blockquote>“Someone has to pay for it. It’s not money that’s disappeared.” — Township administration</blockquote>",
     "<blockquote>“Someone has to pay for it. It’s not money that’s disappeared.” — Township staff</blockquote>"),
])

patch("autumn-in-the-country-2000-russell-grant-2026.html", [
    ("<p>Staff was not objecting to the festival itself. Administration said an “important change” in the budget had arrived and more information was being sought from organizers before a formal recommendation could be completed.</p>",
     "<p>Staff was not objecting to the festival itself. Township staff said an “important change” in the budget had arrived and more information was being sought from organizers before a formal recommendation could be completed.</p>"),
])

patch("index.html", [
    ("<p>Staff says the diversified borrowing plan can save millions while spreading future refinancing risk. Coun. Charles Armstrong calls it “prudent.”</p>",
     "<p>Treasurer Sébastien Dagenais says the diversified borrowing plan can save millions while spreading future refinancing risk. Coun. Charles Armstrong calls it “prudent.”</p>"),
    ("<p>“We’re now looking at the end of September,” staff told council. A rebate question is also on the table.</p>",
     "<p>“We’re now looking at the end of September,” infrastructure executive Jonathan Bourgon told council. A rebate question is also on the table.</p>"),
])
