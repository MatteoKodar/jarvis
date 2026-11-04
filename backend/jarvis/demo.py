"""Reproducerbart internt fotbollsflöde. Ingen datainsamling simuleras som verklig."""
from .models import AgentResult, Claim


def run(task):
    if task["phase"] == "plan":
        return AgentResult(summary="DEMO · Föreslår en avgränsad granskning av fotbollsoddsens datakvalitet. Inga matcher har hämtats och inga spel har placerats.",
                           rationale="Tidsstämplar, 90-minutersmarknad, referensberoenden och kostnader måste kontrolleras före lönsamhetsprövning.",
                           next_action="Granska underlaget för fotbollens 1X2-marknad", proposed_agent="researcher",
                           risks="Syntetiska flödesexempel bevisar inte vinst. Verklig offerttillgång är inte verifierad.",
                           alternatives="Avstå från signaler, begär dokumenterad oddsdata eller granska den historiska förlusten.")
    if task["phase"] == "review":
        return AgentResult(summary="DEMO · Kritikergranskning klar. Utan verifierade offerttider, priser och fulla kostnader kan ingen lönsamhetsfördel fastställas.",
                           rationale="Endast intern demonstration. Fortsatta insatser saknar stöd och riktiga spel är avstängda.", blocked=True)
    return AgentResult(summary="DEMO · Datakvalitetens granskningspunkter har sammanställts: rätt match och marknad, offertålder, referensberoenden och fullständig kostnadslogg. Inga verkliga odds har hämtats.",
                       rationale="Underlag krävs för att skilja en beräknad avvikelse från en genomförbar fördel.",
                       claims=[Claim(text="Detta är ett förskrivet fotbollsexempel, inte ett genomfört odds- eller vinsttest.", kind="ANTAGANDE")])

