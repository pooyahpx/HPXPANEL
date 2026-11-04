import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '@/components/ui/accordion'
import { cn } from '@/lib/utils'
import { BookOpen, ShieldAlert } from 'lucide-react'

interface Props {
  fa?: boolean
  className?: string
}

/**
 * In-panel operator guide for Direct Spoof tunnels.
 * Visual language follows HPXPANEL ops tokens (slate + status green accent).
 */
export function DirectSpoofGuide({ fa = false, className }: Props) {
  return (
    <section
      className={cn(
        'rounded-lg border border-border/80 bg-card/60 p-3 shadow-sm backdrop-blur-sm',
        className,
      )}
      dir={fa ? 'rtl' : 'ltr'}
    >
      <div className="mb-2 flex items-start gap-2">
        <BookOpen className="text-primary mt-0.5 size-4 shrink-0" aria-hidden />
        <div>
          <h3 className="text-sm font-semibold tracking-tight">
            {fa ? 'راهنمای کامل Direct Spoof' : 'Direct Spoof complete guide'}
          </h3>
          <p className="text-muted-foreground mt-0.5 text-xs leading-relaxed">
            {fa
              ? 'تونل اسپوف فقط روی Direct L3 است — مثل ICMP جداست و به Reverse دست نمی‌زند.'
              : 'Spoof is Direct L3 only — a separate path like ICMP; Reverse stays untouched.'}
          </p>
        </div>
      </div>

      <div className="mb-3 flex items-start gap-2 rounded-md border border-amber-500/30 bg-amber-500/10 px-2.5 py-2 text-xs text-amber-900 dark:text-amber-200">
        <ShieldAlert className="mt-0.5 size-3.5 shrink-0" aria-hidden />
        <p>
          {fa
            ? 'هر دو سرور لینوکس + root (CAP_NET_RAW) و موتور ≥ ۱.۹.۰ لازم است. پروفایل پکت و Stealth باید در دو طرف یکی باشد.'
            : 'Both ends need Linux + root (CAP_NET_RAW) and engine ≥ 1.9.0. Packet profile and Stealth must match on both sides.'}
        </p>
      </div>

      <Accordion type="multiple" defaultValue={['why', 'steps']} className="w-full">
        <AccordionItem value="why">
          <AccordionTrigger className="cursor-pointer py-2 text-sm hover:no-underline">
            {fa ? 'چرا فقط Direct؟' : 'Why Direct only?'}
          </AccordionTrigger>
          <AccordionContent className="text-muted-foreground text-xs leading-relaxed">
            {fa
              ? 'تونل Reverse چند سشن هم‌زمان دارد و پکت با مبدأ جعلی راهی برای جدا کردن آن‌ها ندارد؛ همه روی یک آدرس می‌نشینند و تونل «وصل» نشان می‌دهد ولی چیزی رد نمی‌کند. Direct یک سشن دارد و این carrier فقط همان شکل را پوشش می‌دهد.'
              : 'A reverse tunnel has many sessions; forged-source packets share one address so demux collapses — the tunnel looks up but carries nothing. Direct has one session, which is the shape this carrier can serve.'}
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="steps">
          <AccordionTrigger className="cursor-pointer py-2 text-sm hover:no-underline">
            {fa ? 'مراحل ساخت اسپوف در Pulse' : 'How to build Spoof in Pulse'}
          </AccordionTrigger>
          <AccordionContent className="text-muted-foreground space-y-2 text-xs leading-relaxed">
            <ol className="list-decimal space-y-1.5 ps-4">
              <li>
                {fa
                  ? 'Intent را روی «Direct Spoof» بگذار و Preview بزن — فقط پروفایل‌های اسپوف بالا می‌آیند.'
                  : 'Set Intent to “Direct Spoof” and Preview — only spoof profiles rank high.'}
              </li>
              <li>
                {fa
                  ? 'UDP را برای اولین اجرا انتخاب کن (پیشنهادی). ICMP وقتی UDP فیلتر است؛ Stealth وقتی DPI شکل پکت را می‌بیند.'
                  : 'Pick UDP for the first run (recommended). ICMP when UDP is filtered; Stealth when DPI fingerprints the flow.'}
              </li>
              <li>
                {fa
                  ? 'IP عمومی ایران و خارج + پورت تونل را وارد کن. پنل روی ایران، IP واقعی خارج را به‌عنوان spoof_peer_ip می‌نویسد.'
                  : 'Enter Iran/Abroad public IPs + tunnel port. The panel sets Iran’s spoof_peer_ip to the Abroad real IPv4.'}
              </li>
              <li>
                {fa
                  ? 'مبدأ جعلی را خالی بگذار تا مسیر بدون جعل ثابت شود؛ بعد فقط آدرسی که واقعاً می‌رسد را بگذار.'
                  : 'Leave forged source empty until the path works unforged; then pin only addresses that actually arrive.'}
              </li>
              <li>
                {fa
                  ? 'Create Pulse → دستور join را روی هر دو سرور اجرا کن (root). Port forward مثل بقیهٔ Pulse است.'
                  : 'Create Pulse → run join commands on both servers as root. Port forwards work like any other Pulse.'}
              </li>
            </ol>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="pairing">
          <AccordionTrigger className="cursor-pointer py-2 text-sm hover:no-underline">
            {fa ? 'قرارداد جفت بودن تنظیمات' : 'Paired settings contract'}
          </AccordionTrigger>
          <AccordionContent className="text-muted-foreground space-y-2 text-xs leading-relaxed">
            <p className="font-medium text-foreground">{fa ? 'باید در دو طرف یکی باشد:' : 'Must match on both ends:'}</p>
            <ul className="list-disc space-y-1 ps-4">
              <li>spoof_profile / uplink / downlink</li>
              <li>{fa ? 'Stealth (padding و fake TLS)' : 'Stealth (padding and fake TLS)'}</li>
              <li>spoof_icmp_reply {fa ? '(فقط پروفایل ICMP)' : '(ICMP profiles only)'}</li>
            </ul>
            <p className="font-medium text-foreground">{fa ? 'محلی — لازم نیست یکی باشد:' : 'Local — need not match:'}</p>
            <ul className="list-disc space-y-1 ps-4">
              <li>TTL jitter / DSCP / port shuffle / interface / XDP / sockbuf / MTU</li>
            </ul>
            <p>
              {fa
                ? 'روی سرور ایران spoof_peer_ip = IP واقعی خارج اجباری است (پنل خودکار پر می‌کند).'
                : 'On Iran, spoof_peer_ip = Abroad’s real IPv4 is required (panel autofills it).'}
            </p>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="tester">
          <AccordionTrigger className="cursor-pointer py-2 text-sm hover:no-underline">
            {fa ? 'اثبات مبدأ جعلی قبل از فورج' : 'Prove forged sources before forging'}
          </AccordionTrigger>
          <AccordionContent className="text-muted-foreground space-y-2 text-xs leading-relaxed">
            <p>
              {fa
                ? 'بیشتر شکست‌ها این است که provider پکت جعلی را drop می‌کند. اول تونل را بدون spoof_src_ip بالا بیاور. برای سنجش آدرس‌های جعلی، روی موتور BackPack/HPX از Spoof Tester استفاده کن:'
                : 'Most failures are providers dropping forged packets. Bring the tunnel up with empty spoof_src_ip first. To map which forged addresses survive, use the engine Spoof Tester:'}
            </p>
            <ol className="list-decimal space-y-1.5 ps-4">
              <li>{fa ? 'اول Receiver را روی یک سرور شروع کن (پورت مثلاً ۴۵۰۰۰ را باز کن).' : 'Start the Receiver on one host first (open e.g. UDP 45000).'}</li>
              <li>{fa ? 'Sender را روی سرور دیگر با IP واقعی گیرنده و لیست/CIDR کاندید اجرا کن.' : 'Run Sender on the other host with the receiver’s REAL IP and a candidate list/CIDR.'}</li>
              <li>{fa ? 'فقط IPهایی که LOSS قابل قبول دارند را در مبدأ جعلی بگذار؛ نقش‌ها را عوض کن تا جهت دیگر هم سنجیده شود.' : 'Feed only low-loss IPs into forged source; swap roles to map the other direction.'}</li>
            </ol>
            <p>
              {fa
                ? 'اگر همه ۰/۵ بودند، سرویس‌دهنده جعل را عبور نمی‌دهد — تنظیمات پنل آن را درست نمی‌کند.'
                : 'If everything is 0/5, the provider drops spoofed packets — no panel setting can fix that.'}
            </p>
          </AccordionContent>
        </AccordionItem>

        <AccordionItem value="troubleshoot">
          <AccordionTrigger className="cursor-pointer py-2 text-sm hover:no-underline">
            {fa ? 'عیب‌یابی سریع' : 'Quick troubleshooting'}
          </AccordionTrigger>
          <AccordionContent className="text-muted-foreground text-xs leading-relaxed">
            <ul className="list-disc space-y-1.5 ps-4">
              <li>
                {fa
                  ? 'وصل می‌شود ولی ترافیک نیست → مبدأ جعلی drop شده یا پروفایل دو طرف فرق دارد؛ تستر را بزن / Stealth را هم‌سان کن.'
                  : 'Up but no traffic → forged source dropped or profile mismatch; retest / align Stealth.'}
              </li>
              <li>
                {fa
                  ? 'هیچ چیز حتی بدون جعل → spoof_peer_ip روی ایران خالی یا پروفایل ناسازگار.'
                  : 'Nothing even unforged → Iran spoof_peer_ip missing or profile mismatch.'}
              </li>
              <li>
                {fa
                  ? 'سرعت خیلی کمتر از لینک → spoof_sockbuf را بالا ببر؛ padding بیهوده را خاموش کن.'
                  : 'Throughput far below the link → raise spoof_sockbuf; turn off needless padding.'}
              </li>
              <li>
                {fa
                  ? 'فایل بزرگ خراب، کوچک OK → spoof_mtu را پایین بیاور.'
                  : 'Large transfers fail, small OK → lower spoof_mtu.'}
              </li>
            </ul>
          </AccordionContent>
        </AccordionItem>
      </Accordion>
    </section>
  )
}
