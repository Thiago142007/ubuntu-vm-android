package com.thiagovm.ubuntu

import android.annotation.SuppressLint
import android.graphics.Bitmap
import android.os.Bundle
import android.view.View
import android.webkit.WebChromeClient
import android.webkit.WebResourceError
import android.webkit.WebResourceRequest
import android.webkit.WebSettings
import android.webkit.WebView
import android.webkit.WebViewClient
import android.widget.Button
import android.widget.ProgressBar
import android.widget.TextView
import android.widget.Toast
import androidx.activity.OnBackPressedCallback
import androidx.appcompat.app.AppCompatActivity

class MainActivity : AppCompatActivity() {

    private lateinit var webView: WebView
    private lateinit var progressBar: ProgressBar
    private lateinit var tvStatus: TextView
    private lateinit var btnReload: Button
    private lateinit var btnFullscreen: Button
    private lateinit var btnStart: Button
    private lateinit var btnRestart: Button
    private lateinit var btnStop: Button
    private lateinit var btnBios: Button
    private lateinit var btnKeyUp: Button
    private lateinit var btnKeyDown: Button
    private lateinit var btnKeyLeft: Button
    private lateinit var btnKeyRight: Button
    private lateinit var btnKeyEnter: Button
    private lateinit var btnKeyTab: Button
    private lateinit var btnKeyEsc: Button
    private lateinit var btnKeyKeyboard: Button

    private val vncUrl = "http://127.0.0.1:6080/vnc.html?autoconnect=true&resize=remote"
    private var isFullscreen = false

    @SuppressLint("SetJavaScriptEnabled")
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        webView = findViewById(R.id.webViewVnc)
        progressBar = findViewById(R.id.progressBar)
        tvStatus = findViewById(R.id.tvStatus)
        btnReload = findViewById(R.id.btnReload)
        btnFullscreen = findViewById(R.id.btnFullscreen)
        btnStart = findViewById(R.id.btnStart)
        btnRestart = findViewById(R.id.btnRestart)
        btnStop = findViewById(R.id.btnStop)
        btnBios = findViewById(R.id.btnBios)

        btnKeyUp = findViewById(R.id.btnKeyUp)
        btnKeyDown = findViewById(R.id.btnKeyDown)
        btnKeyLeft = findViewById(R.id.btnKeyLeft)
        btnKeyRight = findViewById(R.id.btnKeyRight)
        btnKeyEnter = findViewById(R.id.btnKeyEnter)
        btnKeyTab = findViewById(R.id.btnKeyTab)
        btnKeyEsc = findViewById(R.id.btnKeyEsc)
        btnKeyKeyboard = findViewById(R.id.btnKeyKeyboard)

        setupWebView()

        btnReload.setOnClickListener {
            tvStatus.text = "Status: Recarregando GUI do Ubuntu..."
            progressBar.visibility = View.VISIBLE
            webView.reload()
        }

        btnFullscreen.setOnClickListener {
            toggleFullscreen()
        }

        btnStart.setOnClickListener {
            sendVmApiCommand("start", "Iniciando VM...")
        }

        btnRestart.setOnClickListener {
            sendVmApiCommand("restart", "Reiniciando VM...")
        }

        btnStop.setOnClickListener {
            sendVmApiCommand("stop", "Desligando VM...")
        }

        btnBios.setOnClickListener {
            sendVmApiCommand("bios", "Iniciando VM no modo BIOS...")
        }

        // Virtual Navigation Keys Listeners
        btnKeyUp.setOnClickListener {
            sendVirtualKey("ArrowUp", android.view.KeyEvent.KEYCODE_DPAD_UP)
        }

        btnKeyDown.setOnClickListener {
            sendVirtualKey("ArrowDown", android.view.KeyEvent.KEYCODE_DPAD_DOWN)
        }

        btnKeyLeft.setOnClickListener {
            sendVirtualKey("ArrowLeft", android.view.KeyEvent.KEYCODE_DPAD_LEFT)
        }

        btnKeyRight.setOnClickListener {
            sendVirtualKey("ArrowRight", android.view.KeyEvent.KEYCODE_DPAD_RIGHT)
        }

        btnKeyEnter.setOnClickListener {
            sendVirtualKey("Enter", android.view.KeyEvent.KEYCODE_ENTER)
        }

        btnKeyTab.setOnClickListener {
            sendVirtualKey("Tab", android.view.KeyEvent.KEYCODE_TAB)
        }

        btnKeyEsc.setOnClickListener {
            sendVirtualKey("Escape", android.view.KeyEvent.KEYCODE_ESCAPE)
        }

        btnKeyKeyboard.setOnClickListener {
            showSoftwareKeyboard()
        }

        loadVnc()
        setupOnBackPressed()
    }

    @SuppressLint("SetJavaScriptEnabled")
    private fun setupWebView() {
        val settings = webView.settings
        settings.javaScriptEnabled = true
        settings.domStorageEnabled = true
        settings.databaseEnabled = true
        settings.useWideViewPort = true
        settings.loadWithOverviewMode = true
        settings.builtInZoomControls = true
        settings.displayZoomControls = false
        settings.allowFileAccess = true
        settings.allowContentAccess = true
        settings.mixedContentMode = WebSettings.MIXED_CONTENT_ALWAYS_ALLOW

        webView.webChromeClient = object : WebChromeClient() {
            override fun onProgressChanged(view: WebView?, newProgress: Int) {
                if (newProgress == 100) {
                    progressBar.visibility = View.GONE
                } else {
                    progressBar.visibility = View.VISIBLE
                }
            }
        }

        webView.webViewClient = object : WebViewClient() {
            override fun onPageStarted(view: WebView?, url: String?, favicon: Bitmap?) {
                super.onPageStarted(view, url, favicon)
                tvStatus.text = "Status: Conectando..."
                progressBar.visibility = View.VISIBLE
            }

            override fun onPageFinished(view: WebView?, url: String?) {
                super.onPageFinished(view, url)
                tvStatus.text = "Status: Ubuntu GUI Conectado ($url)"
                progressBar.visibility = View.GONE
            }

            override fun onReceivedError(
                view: WebView?,
                request: WebResourceRequest?,
                error: WebResourceError?
            ) {
                super.onReceivedError(view, request, error)
                if (request?.isForMainFrame == true) {
                    tvStatus.text = "Erro ao conectar! Inicie a VM no Termux: python3 ubuntu_vm_manager.py start"
                    Toast.makeText(
                        this@MainActivity,
                        "Servidor VNC offline. Execute 'ubuntu_vm_manager.py start'",
                        Toast.LENGTH_LONG
                    ).show()
                }
            }
        }
    }

    private fun loadVnc() {
        webView.loadUrl(vncUrl)
    }

    private fun toggleFullscreen() {
        isFullscreen = !isFullscreen
        if (isFullscreen) {
            window.decorView.systemUiVisibility = (
                View.SYSTEM_UI_FLAG_FULLSCREEN
                or View.SYSTEM_UI_FLAG_HIDE_NAVIGATION
                or View.SYSTEM_UI_FLAG_IMMERSIVE_STICKY
            )
            btnFullscreen.text = "Sair da Tela Cheia"
        } else {
            window.decorView.systemUiVisibility = View.SYSTEM_UI_FLAG_VISIBLE
            btnFullscreen.text = "Tela Cheia"
        }
    }

    private fun setupOnBackPressed() {
        onBackPressedDispatcher.addCallback(this, object : OnBackPressedCallback(true) {
            override fun handleOnBackPressed() {
                if (webView.canGoBack()) {
                    webView.goBack()
                } else {
                    finish()
                }
            }
        })
    }

    private fun sendVirtualKey(keyName: String, keyCode: Int) {
        val downEvent = android.view.KeyEvent(android.view.KeyEvent.ACTION_DOWN, keyCode)
        val upEvent = android.view.KeyEvent(android.view.KeyEvent.ACTION_UP, keyCode)
        webView.dispatchKeyEvent(downEvent)
        webView.dispatchKeyEvent(upEvent)

        val js = """
            (function() {
                var target = document.querySelector('canvas') || document.body;
                var evtDown = new KeyboardEvent('keydown', {key: '$keyName', code: '$keyName', keyCode: $keyCode, which: $keyCode, bubbles: true});
                var evtUp = new KeyboardEvent('keyup', {key: '$keyName', code: '$keyName', keyCode: $keyCode, which: $keyCode, bubbles: true});
                target.dispatchEvent(evtDown);
                target.dispatchEvent(evtUp);
            })();
        """.trimIndent()
        webView.evaluateJavascript(js, null)
    }

    private fun showSoftwareKeyboard() {
        val imm = getSystemService(INPUT_METHOD_SERVICE) as? android.view.inputmethod.InputMethodManager
        webView.requestFocus()
        imm?.showSoftInput(webView, android.view.inputmethod.InputMethodManager.SHOW_IMPLICIT)
        webView.evaluateJavascript("if (window.UI && UI.toggleKeyboard) { UI.toggleKeyboard(); }", null)
    }

    private fun sendVmApiCommand(action: String, statusMsg: String) {
        tvStatus.text = "Status: $statusMsg"
        progressBar.visibility = View.VISIBLE
        Thread {
            try {
                val url = java.net.URL("http://127.0.0.1:6081/api/$action")
                val connection = url.openConnection() as java.net.HttpURLConnection
                connection.connectTimeout = 3000
                connection.readTimeout = 3000
                connection.requestMethod = "GET"
                val responseCode = connection.responseCode
                connection.disconnect()
                runOnUiThread {
                    Toast.makeText(this, "Comando '$action' enviado ($responseCode)", Toast.LENGTH_SHORT).show()
                    webView.postDelayed({
                        webView.reload()
                    }, 2000)
                }
            } catch (e: Exception) {
                runOnUiThread {
                    Toast.makeText(this, "Erro API VM: ${e.localizedMessage}", Toast.LENGTH_LONG).show()
                    progressBar.visibility = View.GONE
                }
            }
        }.start()
    }
}
