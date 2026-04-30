import Link from "next/link";

export default function ResponsibilityPage() {
	return (
		<div className="mx-auto w-full max-w-4xl px-6 py-20 md:py-28">
			<div className="space-y-8">
				<div className="space-y-4">
					<p className="text-sm font-semibold uppercase tracking-widest text-neutral-500">
						Project Responsibility
					</p>
					<h1 className="text-3xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 md:text-5xl">
						NBDoctor supports clinical reasoning, but does not replace medical judgment.
					</h1>
					<p className="text-base leading-7 text-neutral-600 dark:text-neutral-300">
						NBDoctor is an assistant for information synthesis and decision support. Final
						medical decisions, diagnoses, treatment plans, and patient care actions must
						always be reviewed and approved by a licensed physician.
					</p>
				</div>

				<div className="rounded-2xl border border-neutral-200 bg-white p-6 shadow-sm dark:border-neutral-800 dark:bg-neutral-950">
					<h2 className="text-xl font-semibold text-neutral-900 dark:text-neutral-100">
						Important Disclaimer
					</h2>
					<ul className="mt-4 space-y-3 text-sm leading-6 text-neutral-600 dark:text-neutral-300">
						<li>
							NBDoctor may generate incomplete or incorrect suggestions and should not be
							used as the sole basis for patient decisions.
						</li>
						<li>
							Clinicians are responsible for validating all outputs against clinical
							guidelines, medical records, and direct patient assessment.
						</li>
						<li>
							Emergency and high-risk decisions must follow institutional protocols and
							human-led escalation paths.
						</li>
					</ul>
				</div>

				<div className="text-sm text-neutral-600 dark:text-neutral-300">
					Need clarification for your organization?{" "}
					<Link href="/contact" className="font-semibold text-neutral-900 underline dark:text-neutral-100">
						Contact us
					</Link>
					.
				</div>
			</div>
		</div>
	);
}
