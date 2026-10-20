package com.aion.chat;

import java.net.URI;
import java.util.Locale;

/** Private home endpoints only. Validation performs no network lookup. */
final class ShenXiaoEndpoint {
    private ShenXiaoEndpoint() {}

    static String normalize(String value) {
        try {
            URI uri = new URI(value.trim());
            String scheme = uri.getScheme();
            if (scheme == null) return null;
            scheme = scheme.toLowerCase(Locale.ROOT);
            if (!scheme.equals("http") && !scheme.equals("https")) return null;
            String host = uri.getHost();
            if (host == null || !privateHost(host) || uri.getUserInfo() != null
                    || uri.getFragment() != null || uri.getQuery() != null
                    || uri.getPort() == 0 || uri.getPort() > 65535) return null;
            String path = uri.getPath();
            if (path != null && !path.isEmpty() && !path.equals("/")
                    && !path.equals("/chat")) return null;
            return new URI(scheme, null, host.toLowerCase(Locale.ROOT),
                    uri.getPort(), "/chat", null, null).toASCIIString();
        } catch (Exception invalid) {
            return null;
        }
    }

    private static boolean privateHost(String raw) {
        String host = raw.toLowerCase(Locale.ROOT);
        if (host.equals("localhost") || host.equals("[::1]") || host.equals("::1")) return true;
        if (host.endsWith(".ts.net") && host.length() > ".ts.net".length()) return true;
        String[] parts = host.split("\\.", -1);
        if (parts.length != 4) return false;
        int[] octets = new int[4];
        for (int i = 0; i < 4; i++) {
            if (!parts[i].matches("0|[1-9][0-9]{0,2}")) return false;
            octets[i] = Integer.parseInt(parts[i]);
            if (octets[i] > 255) return false;
        }
        return octets[0] == 10 || octets[0] == 127
                || (octets[0] == 172 && octets[1] >= 16 && octets[1] <= 31)
                || (octets[0] == 192 && octets[1] == 168)
                || (octets[0] == 100 && octets[1] >= 64 && octets[1] <= 127);
    }

    static boolean sameOrigin(String base, String target) {
        try {
            URI left = new URI(base);
            URI right = new URI(target);
            return right.getUserInfo() == null
                    && left.getScheme().equalsIgnoreCase(right.getScheme())
                    && left.getHost().equalsIgnoreCase(right.getHost())
                    && effectivePort(left) == effectivePort(right);
        } catch (Exception invalid) {
            return false;
        }
    }

    private static int effectivePort(URI uri) {
        return uri.getPort() == -1 ? ("https".equalsIgnoreCase(uri.getScheme()) ? 443 : 80)
                : uri.getPort();
    }
}
