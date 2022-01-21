# Generated by Django 3.2.6 on 2022-01-17 05:47

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='clientInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('clientId', models.CharField(max_length=100)),
                ('clientSecret', models.CharField(max_length=100)),
            ],
        ),
        migrations.CreateModel(
            name='User',
            fields=[
                ('email_id', models.CharField(max_length=40, unique=True)),
                ('name', models.CharField(max_length=30)),
                ('phone', models.CharField(max_length=15)),
                ('user_uuid', models.CharField(max_length=50, primary_key=True, serialize=False, unique=True)),
                ('client_id', models.CharField(max_length=15, null=True)),
            ],
        ),
        migrations.CreateModel(
            name='SubscriptionData',
            fields=[
                ('subscriptionId', models.CharField(max_length=30, unique=True)),
                ('planId', models.IntegerField()),
                ('expiresOn', models.CharField(max_length=40)),
                ('subReferenceId', models.IntegerField(primary_key=True, serialize=False)),
                ('status', models.CharField(max_length=20)),
                ('addedon', models.CharField(max_length=50)),
                ('authLink', models.CharField(max_length=40)),
                ('currentCycle', models.IntegerField()),
                ('user_uuid', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='customapi.user')),
            ],
        ),
        migrations.CreateModel(
            name='PaymentData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('paymentId', models.IntegerField()),
                ('scheduledOn', models.CharField(max_length=40)),
                ('initiatedOn', models.CharField(max_length=40)),
                ('amount', models.FloatField()),
                ('paymentstatus', models.CharField(max_length=20)),
                ('retryAttempts', models.IntegerField()),
                ('subReferenceId', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='customapi.subscriptiondata')),
            ],
        ),
    ]
