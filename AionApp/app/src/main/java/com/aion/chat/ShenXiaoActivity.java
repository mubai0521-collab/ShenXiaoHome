package com.aion.chat;

import android.annotation.SuppressLint;
import android.graphics.Color;
import android.os.Bundle;
import android.view.View;
import android.webkit.PermissionRequest;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import androidx.appcompat.app.AppCompatActivity;

/** No native JS bridges, legacy services or runtime permission prompts. */
public final class ShenXiaoActivity extends AppCompatActivity {
    private WebView webView;
    private String endpoint;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        showAddressPicker();
    }

    private void showAddressPicker() {
        destroyWebView();
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        int space = (int) (24 * getResources().getDisplayMetrics().density);
        layout.setPadding(space, space * 2, space, space);
        layout.setBackgroundColor(Color.rgb(246, 249, 251));
        TextView title = new TextView(this);
        title.setText("沈鸮小家");
        title.setTextSize(28);
        layout.addView(title);
        TextView hint = new TextView(this);
        hint.setText("填入电脑的局域网或 Tailscale 地址。\n电脑上的服务启动后，就可以进来了。");
        hint.setPadding(0, space, 0, space);
        layout.addView(hint);
        EditText address = new EditText(this);
        address.setSingleLine(true);
        address.setHint("http://你的私网地址:8080/chat");
        address.setInputType(android.text.InputType.TYPE_CLASS_TEXT
                | android.text.InputType.TYPE_TEXT_VARIATION_URI);
        address.setText(getSharedPreferences("shenxiao", MODE_PRIVATE)
                .getString("endpoint", ""));
        layout.addView(address);
        Button connect = new Button(this);
        connect.setText("进家门");
        connect.setOnClickListener(view -> {
            String target = ShenXiaoEndpoint.normalize(address.getText().toString());
            if (target == null) {
                Toast.makeText(this, "请填写局域网或 Tailscale 的 HTTP/HTTPS 地址",
                        Toast.LENGTH_LONG).show();
                return;
            }
            getSharedPreferences("shenxiao", MODE_PRIVATE).edit()
                    .putString("endpoint", target).apply();
            openChat(target);
        });
        layout.addView(connect);
        setContentView(layout);
    }

    @SuppressLint("SetJavaScriptEnabled")
    private void openChat(String target) {
        endpoint = target;
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        Button changeAddress = new Button(this);
        changeAddress.setText("连接设置");
        changeAddress.setOnClickListener(view -> showAddressPicker());
        layout.addView(changeAddress);
        webView = new WebView(this);
        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        settings.setMediaPlaybackRequiresUserGesture(true);
        settings.setSupportMultipleWindows(false);
        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(PermissionRequest request) {
                runOnUiThread(request::deny);
            }
        });
        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                return !ShenXiaoEndpoint.sameOrigin(endpoint, request.getUrl().toString());
            }

            @Override
            public void onPageStarted(WebView view, String url, android.graphics.Bitmap icon) {
                if (!ShenXiaoEndpoint.sameOrigin(endpoint, url)) view.stopLoading();
            }
        });
        layout.addView(webView, new LinearLayout.LayoutParams(
                LinearLayout.LayoutParams.MATCH_PARENT, 0, 1));
        setContentView(layout);
        webView.loadUrl(target);
    }

    @Override
    public void onBackPressed() {
        if (webView != null && webView.canGoBack()) webView.goBack();
        else if (webView != null) showAddressPicker();
        else super.onBackPressed();
    }

    private void destroyWebView() {
        if (webView == null) return;
        webView.stopLoading();
        webView.setVisibility(View.GONE);
        android.view.ViewParent parent = webView.getParent();
        if (parent instanceof android.view.ViewGroup) {
            ((android.view.ViewGroup) parent).removeView(webView);
        }
        webView.destroy();
        webView = null;
    }

    @Override
    protected void onPause() {
        if (webView != null) webView.onPause();
        super.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (webView != null) webView.onResume();
    }

    @Override
    protected void onDestroy() {
        destroyWebView();
        super.onDestroy();
    }
}
