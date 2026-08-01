import ScrollFX from "@/components/ScrollFX";
import SiteHeader from "@/components/SiteHeader";
import Hero from "@/components/Hero";
import Translator from "@/components/Translator";
import LanguageStrip from "@/components/LanguageStrip";
import Pillars from "@/components/Pillars";
import HowItWorks from "@/components/HowItWorks";
import SiteFooter from "@/components/SiteFooter";

export default function Home() {
  return (
    <>
      <ScrollFX />
      <SiteHeader />
      <main>
        <Hero />
        <Translator />
        <LanguageStrip />
        <Pillars />
        <HowItWorks />
      </main>
      <SiteFooter />
    </>
  );
}
