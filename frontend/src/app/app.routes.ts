import { Routes } from '@angular/router';
import { DashboardComponent } from './pages/dashboard/dashboard.component';
import { TransactionsComponent } from './pages/transactions/transactions.component';
import { InventoryComponent } from './pages/inventory/inventory.component';
import { ConfigComponent } from './pages/config/config.component';
import { BotStatusComponent } from './pages/bot-status/bot-status.component';

export const routes: Routes = [
  { path: '', redirectTo: 'dashboard', pathMatch: 'full' },
  { path: 'dashboard', component: DashboardComponent },
  { path: 'transactions', component: TransactionsComponent },
  { path: 'inventory', component: InventoryComponent },
  { path: 'config', component: ConfigComponent },
  { path: 'bot-status', component: BotStatusComponent },
];
