package com.sysweeper.android

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import com.sysweeper.android.probe.ProbeEngine
import com.sysweeper.android.probe.ProbeResult
import com.sysweeper.android.probe.Severity
import com.sysweeper.android.ui.SysweeperTheme
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            SysweeperTheme {
                Surface(
                    modifier = Modifier.fillMaxSize(),
                    color = MaterialTheme.colorScheme.background,
                ) {
                    ScannerScreen()
                }
            }
        }
    }
}

@Composable
fun ScannerScreen() {
    val context = LocalContext.current
    var results by remember { mutableStateOf<List<ProbeResult>?>(null) }

    LaunchedEffect(Unit) {
        results = withContext(Dispatchers.IO) { ProbeEngine.scan(context) }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(16.dp),
    ) {
        Text("Sysweeper · Android 诊断", style = MaterialTheme.typography.titleLarge)
        Text(
            "适配 Android 8–14 · 仅读取系统设置，不修改",
            style = MaterialTheme.typography.bodySmall,
        )
        Spacer(Modifier.height(12.dp))

        if (results == null) {
            Row(
                modifier = Modifier.fillMaxWidth(),
                horizontalArrangement = Arrangement.Center,
            ) {
                CircularProgressIndicator()
            }
        } else {
            LazyColumn(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                items(results!!) { ProbeRow(it) }
            }
        }
    }
}

@Composable
fun ProbeRow(r: ProbeResult) {
    val color = when (r.severity) {
        Severity.WARN -> MaterialTheme.colorScheme.error
        Severity.TIP -> MaterialTheme.colorScheme.tertiary
        else -> MaterialTheme.colorScheme.primary
    }
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(r.label, style = MaterialTheme.typography.titleSmall, color = color)
            Text(r.value, style = MaterialTheme.typography.bodyLarge)
            Text(r.advice, style = MaterialTheme.typography.bodySmall)
        }
    }
}
