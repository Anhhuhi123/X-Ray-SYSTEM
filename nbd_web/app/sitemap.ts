import type { MetadataRoute } from "next";

// Returns a date rounded to the current hour (updates only once per hour)
function getHourlyDate(): Date {
	const now = new Date();
	now.setMinutes(0, 0, 0);
	return now;
}

export default function sitemap(): MetadataRoute.Sitemap {
	const lastModified = getHourlyDate();

	return [
		{
			url: "https://www.surfsense.com/responsibility",
			lastModified,
			changeFrequency: "daily",
			priority: 0.9,
		},
		{
			url: "https://www.surfsense.com/changelog",
			lastModified,
			changeFrequency: "daily",
			priority: 0.8,
		},
	];
}
